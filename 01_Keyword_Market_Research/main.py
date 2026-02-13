"""
01_Keyword_Market_Research/main.py — Workflow Orchestrator

Runs the full Keyword & Market Research pipeline end-to-end:

  1. Read niche + seed keywords (from Google Sheets or CLI args)
  2. Expand keywords via DataForSEO API
  3. Cluster + score keywords via AI
  4. Analyze competitors via SERP + AI gap analysis
  5. Save all results to Google Sheets
  6. Push top opportunities to ContentQueue (feeds Workflow 02)
  7. Send notification summary

Usage:
  # Full run (requires .env with real API keys):
  python -m 01_Keyword_Market_Research.main --niche "lead generation" --keywords "crm,email marketing"

  # Dry-run (no API keys needed, uses mock data):
  python -m 01_Keyword_Market_Research.main --dry-run --niche "lead generation" --keywords "crm,email marketing"

  # Read inputs from Google Sheets NicheInputs tab:
  python -m 01_Keyword_Market_Research.main
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure the project root is on sys.path so `shared` can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.config import settings
from shared.logger import get_logger
from shared.notifier import send_notification
from shared.google_sheets import SheetsClient

# Workflow module imports — folder name starts with a digit so we use path-based imports
_wf_dir = str(Path(__file__).resolve().parent)
if _wf_dir not in sys.path:
    sys.path.insert(0, _wf_dir)

from keyword_expander import expand_keywords, get_keyword_suggestions
from ai_clustering import cluster_keywords, flatten_clusters
from competitor_analysis import analyze_competitors, flatten_competitor_gaps
from sheets_writer import save_all_results

log = get_logger("workflow_01")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_pipeline(niche: str, seed_keywords: list[str]) -> dict:
    """
    Execute the full keyword research pipeline.

    Returns a summary dict with counts and timing.
    """
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 01: KEYWORD & MARKET RESEARCH")
    log.info("=" * 70)
    log.info("Niche: %s", niche)
    log.info("Seed keywords: %s", seed_keywords)
    log.info("Dry-run: %s", settings.dry_run)
    log.info("-" * 70)

    # ── Step 1: Expand seed keywords via DataForSEO ──────────────────────
    log.info("STEP 1/6 -- Expanding seed keywords via DataForSEO...")
    seed_data = expand_keywords(seed_keywords)
    log.info("  -> Got %d keyword results", len(seed_data))

    # Also get related keyword suggestions
    log.info("STEP 2/6 -- Getting keyword suggestions...")
    suggestions = get_keyword_suggestions(seed_keywords)
    log.info("  -> Got %d keyword suggestions", len(suggestions))

    # Combine all keyword data
    all_keyword_data = seed_data + suggestions
    log.info("  -> Total keywords to cluster: %d", len(all_keyword_data))

    # ── Step 2: AI Keyword Clustering ────────────────────────────────────
    log.info("STEP 3/6 -- AI keyword expansion + clustering...")
    clustering_result = cluster_keywords(niche, all_keyword_data)
    keyword_rows = flatten_clusters(clustering_result)
    log.info("  -> %d clustered keyword rows", len(keyword_rows))

    # ── Step 3: Competitor Analysis ──────────────────────────────────────
    # Pick top 3 keywords by opportunity score for competitor analysis
    top_keywords_for_analysis = _pick_top_keywords(clustering_result, n=3)
    log.info("STEP 4/6 -- Competitor analysis for: %s", top_keywords_for_analysis)
    competitor_results = analyze_competitors(top_keywords_for_analysis)
    gap_rows = flatten_competitor_gaps(competitor_results)
    log.info("  -> %d competitor gap rows", len(gap_rows))

    # ── Step 4: Save to Google Sheets ────────────────────────────────────
    log.info("STEP 5/6 -- Saving results to Google Sheets...")
    write_summary = save_all_results(keyword_rows, gap_rows)
    log.info("  -> Sheets summary: %s", write_summary)

    # ── Step 5: Send notification ────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    log.info("STEP 6/6 -- Sending notification...")

    notif_body = _build_notification(
        niche, keyword_rows, gap_rows, write_summary, elapsed
    )
    send_notification(
        subject=f"Keyword Research Complete — {len(keyword_rows)} keywords found",
        body=notif_body,
    )

    # ── Summary ──────────────────────────────────────────────────────────
    summary = {
        "niche": niche,
        "seed_keywords": seed_keywords,
        "total_keywords": len(keyword_rows),
        "total_gaps": len(gap_rows),
        "queued_for_content": write_summary.get("ContentQueue", 0),
        "elapsed_seconds": elapsed,
        "dry_run": settings.dry_run,
    }

    log.info("=" * 70)
    log.info("WORKFLOW 01 COMPLETE")
    log.info("Keywords found: %d | Gaps identified: %d | Queued: %d | Time: %ss",
             summary["total_keywords"], summary["total_gaps"],
             summary["queued_for_content"], elapsed)
    log.info("=" * 70)

    # Save summary as local JSON for debugging
    _save_run_summary(summary, clustering_result, competitor_results)

    return summary


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _pick_top_keywords(clustering_result: dict, n: int = 3) -> list[str]:
    """Extract the top N opportunity keywords from clustering result."""
    # Try top_opportunities first
    top_opps = clustering_result.get("top_opportunities", [])
    if top_opps:
        return [kw["keyword"] for kw in top_opps[:n]]

    # Fall back to scanning all clusters
    all_kws = []
    for cluster in clustering_result.get("clusters", []):
        for kw in cluster.get("keywords", []):
            all_kws.append((kw.get("opportunity_score", 0), kw.get("keyword", "")))

    all_kws.sort(reverse=True)
    return [kw for _, kw in all_kws[:n]]


def _build_notification(
    niche: str,
    keyword_rows: list[dict],
    gap_rows: list[dict],
    write_summary: dict,
    elapsed: float,
) -> str:
    """Format the notification body."""
    top_5 = keyword_rows[:5]
    top_list = "\n".join(
        f"  {i+1}. {r['Keyword']} (vol: {r['Volume']}, score: {r['Opportunity Score']}, intent: {r['Intent']})"
        for i, r in enumerate(top_5)
    )

    return f"""
Keyword Research Pipeline -- Complete
======================================

Niche:              {niche}
Total Keywords:     {len(keyword_rows)}
Content Gaps:       {len(gap_rows)}
Queued for Content: {write_summary.get('ContentQueue', 0)}
Run Time:           {elapsed}s
Date:               {datetime.now().strftime('%Y-%m-%d %H:%M')}

Top 5 Keyword Opportunities:
{top_list}

======================================
Check your Google Sheet for full results.
Workflow 02 (Content Strategy) will pick up queued keywords automatically.
"""


def _save_run_summary(
    summary: dict,
    clustering_result: dict,
    competitor_results: list[dict],
) -> None:
    """Save a JSON snapshot of this run to the output/ directory."""
    output_dir = PROJECT_ROOT / "01_Keyword_Market_Research" / "output"
    output_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = output_dir / f"run_{timestamp}.json"

    data = {
        "summary": summary,
        "clustering": clustering_result,
        "competitor_analysis": competitor_results,
    }

    filepath.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    log.info("Run snapshot saved to: %s", filepath)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Workflow 01 — Keyword & Market Research Automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry-run with mock data (no API keys needed):
  python -m 01_Keyword_Market_Research.main --dry-run --niche "lead generation" --keywords "crm,email marketing"

  # Full run (requires .env with API keys):
  python -m 01_Keyword_Market_Research.main --niche "lead generation" --keywords "crm software,lead gen tools"

  # Read inputs from Google Sheets (NicheInputs tab):
  python -m 01_Keyword_Market_Research.main
        """,
    )
    parser.add_argument(
        "--niche", "-n",
        help="Target niche/topic (overrides Google Sheet input)",
    )
    parser.add_argument(
        "--keywords", "-k",
        help="Comma-separated seed keywords (overrides Google Sheet input)",
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Run with mock data — no API calls (overrides .env DRY_RUN)",
    )

    args = parser.parse_args()

    # Override dry-run from CLI flag
    if args.dry_run:
        import shared.config as cfg
        object.__setattr__(cfg.settings, "dry_run", True)

    # Get niche and keywords from CLI args or Google Sheets
    niche = args.niche
    keywords_str = args.keywords

    if niche and keywords_str:
        seed_keywords = [kw.strip() for kw in keywords_str.split(",") if kw.strip()]
    else:
        # Read from Google Sheets NicheInputs tab
        log.info("No CLI args provided — reading from Google Sheets NicheInputs tab…")
        sheets = SheetsClient()
        rows = sheets.read_rows("NicheInputs")

        if not rows:
            log.error("No niche inputs found! Provide --niche and --keywords, or add rows to NicheInputs tab.")
            sys.exit(1)

        row = rows[0]  # Take the first row
        niche = niche or row.get("Niche", "")
        kw_field = keywords_str or row.get("SeedKeywords", "")
        seed_keywords = [kw.strip() for kw in kw_field.split(",") if kw.strip()]

    if not niche:
        log.error("Niche is required. Use --niche or add to NicheInputs tab.")
        sys.exit(1)
    if not seed_keywords:
        log.error("Seed keywords required. Use --keywords or add to NicheInputs tab.")
        sys.exit(1)

    # Run the pipeline
    summary = run_pipeline(niche, seed_keywords)

    # Print final summary
    print(f"\n[OK] Workflow 01 complete! {summary['total_keywords']} keywords -> "
          f"{summary['queued_for_content']} queued for content generation.")


if __name__ == "__main__":
    main()
