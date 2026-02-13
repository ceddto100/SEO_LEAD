"""
05_Auto_Publishing_System/main.py

Orchestrator for Workflow 05: Auto Publishing System.
Reads PublishQueue, validates, publishes to WordPress, submits for indexing,
updates tracking sheets, and notifies downstream workflows.
"""
from __future__ import annotations
import argparse, json, sys, time
from datetime import datetime
from pathlib import Path
from typing import Any

_project_root = str(Path(__file__).resolve().parent.parent)
if _project_root not in sys.path: sys.path.insert(0, _project_root)
_wf_dir = str(Path(__file__).resolve().parent)
if _wf_dir not in sys.path: sys.path.insert(0, _wf_dir)

from shared.config import settings
from shared.logger import get_logger
from shared.notifier import send_notification
from shared.google_sheets import SheetsClient
from publisher import validate_article, format_for_wordpress, publish_to_wordpress, submit_to_google_indexing

log = get_logger("workflow_05")

PUBLISHED_HEADERS = ["Title", "URL", "Slug", "Keyword", "Date", "SEO Score"]

def run_pipeline(articles: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 05: AUTO PUBLISHING SYSTEM")
    log.info("=" * 70)
    log.info("Articles to publish: %d", len(articles))

    published, skipped = [], []
    sheets = SheetsClient()

    for i, article in enumerate(articles, 1):
        title = article.get("Title", "Untitled")
        log.info("ARTICLE %d/%d: %s", i, len(articles), title)

        # REVIEW GATE: require 'approved' status (not just 'ready')
        status = article.get("Status", "").lower()
        if status != "approved":
            log.info("SKIP (status '%s', needs 'approved'): %s", status, title)
            skipped.append({"title": title, "issues": [f"Status is '{status}', not 'approved'"]})
            continue

        valid, issues = validate_article(article)
        if not valid:
            skipped.append({"title": title, "issues": issues})
            continue

        wp_data = format_for_wordpress("", article)
        result = publish_to_wordpress(wp_data)
        url = result.get("link", "")

        submit_to_google_indexing(url)

        sheets.append_rows("PublishedArticles", [{
            "Title": title, "URL": url, "Slug": article.get("Slug", ""),
            "Keyword": article.get("Keyword", ""),
            "Date": datetime.now().strftime("%Y-%m-%d"),
            "SEO Score": article.get("SEO Score", ""),
        }], headers=PUBLISHED_HEADERS)

        published.append({"title": title, "url": url, "slug": article.get("Slug", "")})

    elapsed = round(time.time() - start, 1)
    send_notification(
        subject=f"Published {len(published)} articles",
        body=f"Published: {len(published)}, Skipped: {len(skipped)}, Time: {elapsed}s")

    summary = {"published": len(published), "skipped": len(skipped),
               "elapsed_seconds": elapsed, "timestamp": datetime.now().isoformat()}
    log.info("WORKFLOW 05 COMPLETE: %d published, %d skipped", len(published), len(skipped))
    return summary

def _read_ready_articles(limit=5):
    if settings.dry_run:
        return [{"Title": "Lead Generation Guide", "Slug": "lead-generation-guide",
                 "Keyword": "lead generation", "Meta Title": "Lead Gen Guide | Brand",
                 "Meta Description": "Complete guide to lead gen.", "SEO Score": "82",
                 "Status": "approved", "Publish Date": "2026-02-14"}][:limit]
    sheets = SheetsClient()
    rows = sheets.read_rows("PublishQueue")
    today = datetime.now().strftime("%Y-%m-%d")
    return [r for r in rows if r.get("Status", "").lower() == "approved"
            and r.get("Publish Date", "") <= today][:limit]

def main():
    parser = argparse.ArgumentParser(description="Workflow 05: Auto Publishing")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--limit", "-l", type=int, default=5)
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    articles = _read_ready_articles(args.limit)
    if not articles: print("No articles ready to publish."); return
    summary = run_pipeline(articles)
    print(f"\n[OK] Workflow 05 complete! {summary['published']} published.")

if __name__ == "__main__": main()
