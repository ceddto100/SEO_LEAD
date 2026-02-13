"""
06_Social_Media_Repurposing/main.py

Orchestrator for Workflow 06: Social Media Content Repurposing.
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
from social_generator import generate_social_content

log = get_logger("workflow_06")

SOCIAL_LOG_HEADERS = ["Article Title", "Platform", "Post Text", "Schedule Date", "Status"]

def run_pipeline(articles: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 06: SOCIAL MEDIA REPURPOSING")
    log.info("=" * 70)

    sheets = SheetsClient()
    total_posts = 0

    for i, article in enumerate(articles, 1):
        title = article.get("Title", "")
        url = article.get("URL", "")
        keyword = article.get("Keyword", "")
        log.info("ARTICLE %d/%d: %s", i, len(articles), title)

        social = generate_social_content(title, url, keyword, title[:200])

        # Log each platform post
        platforms = {
            "Twitter": " | ".join(social.get("twitter_thread", [])),
            "LinkedIn": social.get("linkedin", ""),
            "Instagram": social.get("instagram", {}).get("caption", ""),
            "Facebook": social.get("facebook", ""),
            "Pinterest": social.get("pinterest", ""),
        }
        rows = [{"Article Title": title, "Platform": p, "Post Text": text[:500],
                 "Schedule Date": datetime.now().strftime("%Y-%m-%d"), "Status": "scheduled"}
                for p, text in platforms.items() if text]
        sheets.append_rows("SocialPosts", rows, headers=SOCIAL_LOG_HEADERS)
        total_posts += len(rows)

    elapsed = round(time.time() - start, 1)
    send_notification(subject=f"Social Content -- {total_posts} posts created",
                      body=f"Created {total_posts} posts for {len(articles)} articles in {elapsed}s")
    summary = {"articles_processed": len(articles), "posts_created": total_posts,
               "elapsed_seconds": elapsed}
    log.info("WORKFLOW 06 COMPLETE: %d posts", total_posts)
    return summary

def _read_articles(limit=5):
    if settings.dry_run:
        return [{"Title": "Lead Generation Guide", "URL": "https://site.com/blog/lead-gen",
                 "Keyword": "lead generation"}][:limit]
    sheets = SheetsClient()
    return sheets.read_rows("PublishedArticles")[:limit]

def main():
    parser = argparse.ArgumentParser(description="Workflow 06: Social Media")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--limit", "-l", type=int, default=5)
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    articles = _read_articles(args.limit)
    if not articles: print("No articles to repurpose."); return
    summary = run_pipeline(articles)
    print(f"\n[OK] Workflow 06 complete! {summary['posts_created']} social posts created.")

if __name__ == "__main__": main()
