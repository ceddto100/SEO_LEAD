"""
02_Content_Strategy_Blog_Planning/main.py

Orchestrator for Workflow 02: Content Strategy & Blog Planning.

Pipeline steps:
  1. Read new keywords from ContentQueue (status = "new")
  2. Generate AI content strategy (content types, titles, cluster map)
  3. Generate AI blog outlines for each planned article
  4. Build publishing calendar (Mon/Wed/Fri cadence)
  5. Save everything to Google Sheets
  6. Update ContentQueue status to "planned"
  7. Send notification

Usage:
  python 02_Content_Strategy_Blog_Planning/main.py [--dry-run] [--niche "..."]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# ── Ensure project root is on path ───────────────────────────────────────────
_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from shared.config import settings
from shared.logger import get_logger
from shared.notifier import send_notification
from shared.google_sheets import SheetsClient

# Workflow module imports -- folder starts with a digit, use path-based imports
_wf_dir = str(Path(__file__).resolve().parent)
if _wf_dir not in sys.path:
    sys.path.insert(0, _wf_dir)

from content_planner import generate_content_plan
from outline_generator import generate_all_outlines
from calendar_builder import build_calendar
from sheets_writer import save_all_results

log = get_logger("workflow_02")


# ── Pipeline ─────────────────────────────────────────────────────────────────

def run_pipeline(
    niche: str,
    queued_keywords: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Execute the full Content Strategy & Blog Planning pipeline.
    """
    start = time.time()

    log.info("=" * 70)
    log.info("WORKFLOW 02: CONTENT STRATEGY & BLOG PLANNING")
    log.info("=" * 70)
    log.info("Niche: %s", niche)
    log.info("Queued keywords: %d", len(queued_keywords))
    log.info("Dry-run: %s", settings.dry_run)
    log.info("-" * 70)

    # ── Step 1: AI Content Strategy ──────────────────────────────────────
    log.info("STEP 1/5 -- Generating AI content strategy...")
    strategy = generate_content_plan(niche, queued_keywords)
    content_plan = strategy.get("content_plan", [])
    cluster_map = strategy.get("cluster_map", {})
    log.info("  -> %d content items, %d pillar clusters",
             len(content_plan), len(cluster_map))

    # ── Step 2: AI Blog Outlines ─────────────────────────────────────────
    log.info("STEP 2/5 -- Generating AI blog outlines...")
    outlines = generate_all_outlines(content_plan)
    log.info("  -> %d outlines generated", len(outlines))

    # ── Step 3: Build Publishing Calendar ────────────────────────────────
    log.info("STEP 3/5 -- Building publishing calendar...")
    calendar = build_calendar(content_plan)
    log.info("  -> %d calendar entries", len(calendar))

    # ── Step 4: Save to Google Sheets ────────────────────────────────────
    log.info("STEP 4/5 -- Saving results to Google Sheets...")
    processed_keywords = [item.get("keyword", "") for item in content_plan]
    write_summary = save_all_results(
        calendar, outlines, content_plan, cluster_map, processed_keywords
    )
    log.info("  -> Sheets summary: %s", write_summary)

    # ── Step 5: Send notification ────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    log.info("STEP 5/5 -- Sending notification...")

    notif_body = _build_notification(
        niche, calendar, outlines, write_summary, elapsed
    )
    send_notification(
        subject=f"Content Plan Ready -- {len(content_plan)} articles scheduled",
        body=notif_body,
    )

    # ── Summary ──────────────────────────────────────────────────────────
    summary = {
        "niche": niche,
        "total_articles": len(content_plan),
        "outlines_generated": len(outlines),
        "calendar_entries": len(calendar),
        "cluster_pillars": len(cluster_map),
        "sheets_written": write_summary,
        "elapsed_seconds": elapsed,
        "timestamp": datetime.now().isoformat(),
    }

    log.info("=" * 70)
    log.info("WORKFLOW 02 COMPLETE")
    log.info(
        "Articles: %d | Outlines: %d | Pillars: %d | Time: %ss",
        len(content_plan), len(outlines), len(cluster_map), elapsed,
    )
    log.info("=" * 70)

    # Save run snapshot
    _save_run_summary(summary, strategy, outlines, calendar)

    return summary


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_notification(
    niche: str,
    calendar: list[dict[str, Any]],
    outlines: list[dict[str, Any]],
    write_summary: dict[str, int],
    elapsed: float,
) -> str:
    """Build a human-readable notification body."""
    # Calendar preview: first 5 articles
    cal_lines = []
    for entry in calendar[:5]:
        cal_lines.append(
            f"  {entry['Publish Date']} | {entry['Type']:<15} | {entry['Title']}"
        )
    cal_preview = "\n".join(cal_lines) if cal_lines else "  (none)"

    return f"""
Content Strategy Pipeline -- Complete
======================================

Niche:              {niche}
Total Articles:     {len(calendar)}
Outlines Created:   {len(outlines)}
Run Time:           {elapsed}s
Date:               {datetime.now().strftime('%Y-%m-%d %H:%M')}

Upcoming Content Calendar:
{cal_preview}

Sheets Updated:     {write_summary}

======================================
Blog outlines are saved in the BlogOutlines tab.
Workflow 03 (AI Blog Writing) can pick up planned articles next.
"""


def _save_run_summary(
    summary: dict[str, Any],
    strategy: dict[str, Any],
    outlines: list[dict[str, Any]],
    calendar: list[dict[str, Any]],
) -> None:
    """Save a JSON snapshot of this run for debugging."""
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)

    filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = output_dir / filename

    snapshot = {
        "summary": summary,
        "strategy": strategy,
        "calendar": calendar,
        "outlines_count": len(outlines),
        # Don't dump full outlines -- they're large
        "outline_titles": [o.get("title", "") for o in outlines],
    }

    filepath.write_text(json.dumps(snapshot, indent=2, default=str))
    log.info("Run snapshot saved to: %s", filepath)


def _read_queue_keywords() -> list[dict[str, Any]]:
    """
    Read new keywords from the ContentQueue Google Sheet.
    Returns rows where Status = 'new'.
    """
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock ContentQueue data")
        return [
            {"Keyword": "lead generation strategies",
             "Volume": "8100", "Intent": "informational",
             "Opportunity Score": "92", "Status": "new"},
            {"Keyword": "best crm software 2026",
             "Volume": "6600", "Intent": "transactional",
             "Opportunity Score": "88", "Status": "new"},
            {"Keyword": "email marketing automation",
             "Volume": "5400", "Intent": "informational",
             "Opportunity Score": "85", "Status": "new"},
            {"Keyword": "how to generate leads online",
             "Volume": "4400", "Intent": "informational",
             "Opportunity Score": "80", "Status": "new"},
            {"Keyword": "b2b lead generation tools",
             "Volume": "3600", "Intent": "transactional",
             "Opportunity Score": "78", "Status": "new"},
        ]

    sheets = SheetsClient()
    all_rows = sheets.read_rows("ContentQueue")
    new_rows = [r for r in all_rows if r.get("Status", "").lower() == "new"]
    log.info("Found %d new keywords in ContentQueue", len(new_rows))
    return new_rows


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Workflow 02: Content Strategy & Blog Planning",
    )
    parser.add_argument(
        "--niche", "-n",
        default=None,
        help="Business niche (reads from .env NICHE if not set)",
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Run with mock data, no API calls",
    )

    args = parser.parse_args()

    # Override dry_run if CLI flag is set
    if args.dry_run and not settings.dry_run:
        import dataclasses
        object.__setattr__(settings, "dry_run", True)
        log.info("Dry-run mode enabled via CLI flag")

    # Determine niche
    niche = args.niche or settings.niche

    # Read queued keywords
    queued_keywords = _read_queue_keywords()

    if not queued_keywords:
        log.warning("No new keywords found in ContentQueue. Nothing to plan.")
        print("No new keywords in ContentQueue. Run Workflow 01 first.")
        return

    summary = run_pipeline(niche, queued_keywords)

    # Print final summary
    print(f"\n[OK] Workflow 02 complete! {summary['total_articles']} articles planned, "
          f"{summary['outlines_generated']} outlines generated.")


if __name__ == "__main__":
    main()
