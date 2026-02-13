"""
03_AI_Blog_Writing_SEO/main.py

Orchestrator for Workflow 03: AI Blog Writing & SEO Optimization.

Pipeline steps:
  1. Read planned articles from ContentCalendar (status = "planned")
  2. Fetch outline from BlogOutlines sheet
  3. AI writes full HTML article from outline
  4. AI generates SEO metadata (meta title, description, schema, OG tags)
  5. AI runs SEO quality audit (12-factor scoring)
  6. If score < 70, rewrite with audit feedback (max 1 retry)
  7. Resolve internal link placeholders
  8. Save results to Sheets (update calendar + queue for publishing)
  9. Send notification

Usage:
  python 03_AI_Blog_Writing_SEO/main.py [--dry-run] [--niche "..."] [--limit N]
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

from article_writer import write_article
from seo_optimizer import generate_meta, audit_seo, needs_rewrite, format_audit_feedback
from link_resolver import resolve_links
from sheets_writer import save_all_results

log = get_logger("workflow_03")

MAX_REWRITES = 1  # Max number of audit-triggered rewrites per article


# ── Pipeline ─────────────────────────────────────────────────────────────────

def run_pipeline(
    articles: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Execute the full AI Blog Writing & SEO pipeline for a batch of articles.
    """
    start = time.time()

    log.info("=" * 70)
    log.info("WORKFLOW 03: AI BLOG WRITING & SEO OPTIMIZATION")
    log.info("=" * 70)
    log.info("Articles to write: %d", len(articles))
    log.info("Dry-run: %s", settings.dry_run)
    log.info("-" * 70)

    results: list[dict[str, Any]] = []
    sheets = SheetsClient()

    for i, article in enumerate(articles, 1):
        title = article.get("Title", "Untitled")
        keyword = article.get("Keyword", "")

        # DEDUP CHECK: skip if already written
        if sheets.has_row("ContentCalendar", "Keyword", keyword):
            existing_rows = sheets.read_rows("ContentCalendar",
                                              filters={"Keyword": keyword})
            if any(r.get("Status", "").lower() == "written" for r in existing_rows):
                log.info("SKIP (already written): %s", title)
                continue

        word_count = int(article.get("Word Count", 2000))
        content_type = article.get("Type", "blog post")
        publish_date = article.get("Publish Date", datetime.now().strftime("%Y-%m-%d"))
        outline_text = article.get("Outline Text", "")

        log.info("=" * 50)
        log.info("ARTICLE %d/%d: %s", i, len(articles), title)
        log.info("=" * 50)

        # ── Step 1: Write the article ────────────────────────────────────
        log.info("STEP 1 -- Writing article...")
        article_html = write_article(
            title=title,
            keyword=keyword,
            word_count=word_count,
            content_type=content_type,
            outline_text=outline_text,
        )
        log.info("  -> Article written (%d chars)", len(article_html))

        # ── Step 2: Generate SEO meta ────────────────────────────────────
        log.info("STEP 2 -- Generating SEO metadata...")
        meta_data = generate_meta(title, keyword, publish_date)
        log.info("  -> Meta: slug=%s", meta_data.get("slug", ""))

        # ── Step 3: SEO Audit ────────────────────────────────────────────
        log.info("STEP 3 -- Running SEO audit...")
        audit_result = audit_seo(article_html, meta_data, word_count)
        seo_score = audit_result.get("overall_score", 0)
        log.info("  -> SEO score: %d/100", seo_score)

        # ── Step 4: Rewrite if score < threshold ─────────────────────────
        rewrite_count = 0
        while needs_rewrite(audit_result) and rewrite_count < MAX_REWRITES:
            rewrite_count += 1
            feedback = format_audit_feedback(audit_result)
            log.info(
                "STEP 4 -- Rewriting article (attempt %d, score was %d)...",
                rewrite_count, seo_score,
            )
            article_html = write_article(
                title=title,
                keyword=keyword,
                word_count=word_count,
                content_type=content_type,
                outline_text=outline_text,
                audit_feedback=feedback,
            )
            # Re-audit
            audit_result = audit_seo(article_html, meta_data, word_count)
            seo_score = audit_result.get("overall_score", 0)
            log.info("  -> New SEO score: %d/100", seo_score)

        # ── Step 5: Resolve internal links ───────────────────────────────
        log.info("STEP 5 -- Resolving internal links...")
        article_html, link_count = resolve_links(article_html)
        log.info("  -> %d links resolved", link_count)

        # ── Step 6: Save to Sheets ───────────────────────────────────────
        log.info("STEP 6 -- Saving to Google Sheets...")
        actual_word_count = len(article_html.split())
        write_summary = save_all_results(
            title=title,
            keyword=keyword,
            meta_data=meta_data,
            publish_date=publish_date,
            seo_score=seo_score,
            word_count=actual_word_count,
        )
        log.info("  -> Sheets: %s", write_summary)

        results.append({
            "title": title,
            "keyword": keyword,
            "slug": meta_data.get("slug", ""),
            "seo_score": seo_score,
            "word_count": actual_word_count,
            "rewrites": rewrite_count,
            "links_resolved": link_count,
            "publish_date": publish_date,
        })

    # ── Notification ─────────────────────────────────────────────────────
    elapsed = round(time.time() - start, 1)
    log.info("STEP 7 -- Sending notification...")

    notif_body = _build_notification(results, elapsed)
    send_notification(
        subject=f"Blog Writing Complete -- {len(results)} articles written",
        body=notif_body,
    )

    # ── Summary ──────────────────────────────────────────────────────────
    summary = {
        "articles_written": len(results),
        "avg_seo_score": round(sum(r["seo_score"] for r in results) / max(len(results), 1)),
        "total_rewrites": sum(r["rewrites"] for r in results),
        "total_links_resolved": sum(r["links_resolved"] for r in results),
        "articles": results,
        "elapsed_seconds": elapsed,
        "timestamp": datetime.now().isoformat(),
    }

    log.info("=" * 70)
    log.info("WORKFLOW 03 COMPLETE")
    log.info(
        "Written: %d | Avg SEO: %d | Rewrites: %d | Time: %ss",
        len(results), summary["avg_seo_score"],
        summary["total_rewrites"], elapsed,
    )
    log.info("=" * 70)

    _save_run_summary(summary)
    return summary


# ── Helpers ──────────────────────────────────────────────────────────────────

def _build_notification(
    results: list[dict[str, Any]],
    elapsed: float,
) -> str:
    """Build a human-readable notification body."""
    article_lines = []
    for r in results:
        article_lines.append(
            f"  {r['publish_date']} | SEO:{r['seo_score']:>3} | "
            f"{r['word_count']:>5}w | {r['title']}"
        )
    article_list = "\n".join(article_lines) if article_lines else "  (none)"

    avg_score = round(sum(r["seo_score"] for r in results) / max(len(results), 1))

    return f"""
Blog Writing Pipeline -- Complete
======================================

Articles Written:   {len(results)}
Average SEO Score:  {avg_score}/100
Total Rewrites:     {sum(r['rewrites'] for r in results)}
Links Resolved:     {sum(r['links_resolved'] for r in results)}
Run Time:           {elapsed}s

Articles:
{article_list}

======================================
Articles are queued in PublishQueue for Workflow 05.
"""


def _save_run_summary(summary: dict[str, Any]) -> None:
    """Save a JSON snapshot of this run for debugging."""
    output_dir = Path(__file__).resolve().parent / "output"
    output_dir.mkdir(exist_ok=True)

    filename = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = output_dir / filename

    filepath.write_text(json.dumps(summary, indent=2, default=str))
    log.info("Run snapshot saved to: %s", filepath)


def _read_planned_articles(limit: int = 5) -> list[dict[str, Any]]:
    """
    Read planned articles from ContentCalendar and their outlines from
    BlogOutlines.
    """
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock planned articles")
        return [
            {
                "Title": "The Complete Guide to Lead Generation Strategies",
                "Keyword": "lead generation strategies",
                "Type": "ultimate guide",
                "Word Count": "3000",
                "Publish Date": "2026-02-14",
                "Outline Text": _mock_outline("lead generation strategies"),
            },
            {
                "Title": "How to Master Email Marketing Automation in 2026",
                "Keyword": "email marketing automation",
                "Type": "how-to tutorial",
                "Word Count": "2000",
                "Publish Date": "2026-02-17",
                "Outline Text": _mock_outline("email marketing automation"),
            },
            {
                "Title": "10 Best CRM Software Tools Compared",
                "Keyword": "best crm software",
                "Type": "listicle",
                "Word Count": "2500",
                "Publish Date": "2026-02-19",
                "Outline Text": _mock_outline("best crm software"),
            },
        ][:limit]

    sheets = SheetsClient()
    calendar_rows = sheets.read_rows("ContentCalendar")
    planned = [r for r in calendar_rows
               if r.get("Status", "").lower() == "planned"]

    # Sort by priority and limit
    planned.sort(key=lambda x: int(x.get("Priority", 5)))
    planned = planned[:limit]

    # Fetch outlines
    outline_rows = sheets.read_rows("BlogOutlines")
    outline_map = {r.get("Keyword", "").lower(): r.get("Outline Text", "")
                   for r in outline_rows}

    for article in planned:
        kw = article.get("Keyword", "").lower()
        article["Outline Text"] = outline_map.get(kw, "")

    log.info("Found %d planned articles", len(planned))
    return planned


def _mock_outline(keyword: str) -> str:
    """Simple mock outline text for dry-run."""
    return f"""
## Introduction
- Hook with compelling statistic about {keyword}
- Why {keyword} matters in 2026

## Understanding {keyword.title()}
### What It Is
### Key Concepts

## Best Practices
### Strategy 1: Content-First Approach
### Strategy 2: Data-Driven Decisions
### Strategy 3: Automation

## Tools and Resources
### Top Paid Tools
### Free Alternatives

## Case Studies
### Example 1: Company X
### Example 2: Company Y

## Key Takeaways

## FAQ
- What is {keyword}?
- How do I get started?
- What are the best tools?
- How much does it cost?
- Is it worth it in 2026?

## Conclusion
"""


# ── CLI entry point ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Workflow 03: AI Blog Writing & SEO Optimization",
    )
    parser.add_argument(
        "--niche", "-n",
        default=None,
        help="Business niche (for context)",
    )
    parser.add_argument(
        "--limit", "-l",
        type=int,
        default=5,
        help="Max articles to write per run (default: 5)",
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true",
        help="Run with mock data, no API calls",
    )

    args = parser.parse_args()

    # Override dry_run if CLI flag is set
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
        log.info("Dry-run mode enabled via CLI flag")

    # Read planned articles
    articles = _read_planned_articles(limit=args.limit)

    if not articles:
        log.warning("No planned articles found. Nothing to write.")
        print("No planned articles in ContentCalendar. Run Workflow 02 first.")
        return

    summary = run_pipeline(articles)

    # Print final summary
    print(f"\n[OK] Workflow 03 complete! {summary['articles_written']} articles written, "
          f"avg SEO score: {summary['avg_seo_score']}/100.")


if __name__ == "__main__":
    main()
