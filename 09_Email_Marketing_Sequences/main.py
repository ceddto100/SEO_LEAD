"""
09_Email_Marketing_Sequences/main.py

Orchestrator for Workflow 09: Email Marketing Sequences.
Generates nurture sequences per segment and weekly newsletters.
"""
from __future__ import annotations
import argparse, json, sys, time
from datetime import datetime, timedelta
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
from email_generator import NURTURE_SEQUENCE, generate_nurture_email, generate_newsletter

log = get_logger("workflow_09")

EMAIL_PERF_HEADERS = ["Campaign", "Subject", "Segment", "Sent", "Date", "Status"]

def run_pipeline(mode: str = "nurture") -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 09: EMAIL MARKETING SEQUENCES (mode: %s)", mode)
    log.info("=" * 70)

    sheets = SheetsClient()

    if mode == "newsletter":
        return _run_newsletter(sheets, start)
    return _run_nurture(sheets, start)

def _run_nurture(sheets, start) -> dict[str, Any]:
    subscribers = _read_subscribers()
    log.info("Subscribers for nurture: %d", len(subscribers))
    emails_total = 0

    for sub in subscribers:
        name = sub.get("name", "Unknown")
        log.info("SUBSCRIBER: %s (%s)", name, sub.get("segment", "general"))
        for idx, step in enumerate(NURTURE_SEQUENCE):
            email = generate_nurture_email(sub, idx, step["type"])
            send_date = (datetime.now() + timedelta(days=step["day"])).strftime("%Y-%m-%d")
            sheets.append_rows("EmailPerformance", [{
                "Campaign": f"Nurture #{idx+1}", "Subject": email.get("subject", ""),
                "Segment": sub.get("segment", ""), "Sent": 0,
                "Date": send_date, "Status": "scheduled",
            }], headers=EMAIL_PERF_HEADERS)
            emails_total += 1

    elapsed = round(time.time() - start, 1)
    send_notification(subject=f"Nurture Sequences -- {emails_total} emails queued",
                      body=f"{len(subscribers)} subscribers, {emails_total} emails, {elapsed}s")
    summary = {"subscribers": len(subscribers), "emails_queued": emails_total,
               "elapsed_seconds": elapsed}
    log.info("WORKFLOW 09 COMPLETE: %d nurture emails", emails_total)
    return summary

def _run_newsletter(sheets, start) -> dict[str, Any]:
    articles = _read_recent_articles()
    log.info("Articles for newsletter: %d", len(articles))
    newsletter = generate_newsletter(articles)

    sheets.append_rows("EmailPerformance", [{
        "Campaign": "Weekly Newsletter", "Subject": newsletter.get("subject", ""),
        "Segment": "all", "Sent": 0,
        "Date": datetime.now().strftime("%Y-%m-%d"), "Status": "draft",
    }], headers=EMAIL_PERF_HEADERS)

    elapsed = round(time.time() - start, 1)
    send_notification(subject=f"Newsletter Ready: {newsletter.get('subject', '')}",
                      body=f"Newsletter covering {len(articles)} articles, {elapsed}s")
    log.info("WORKFLOW 09 COMPLETE: Newsletter generated")
    return {"newsletter_articles": len(articles), "elapsed_seconds": elapsed}

def _read_subscribers():
    if settings.dry_run:
        return [{"name": "Jane Smith", "email": "jane@company.com",
                 "segment": "seo-interested", "lead_magnet": "free-seo-checklist"},
                {"name": "Bob Wilson", "email": "bob@startup.io",
                 "segment": "lead-gen-interested", "lead_magnet": "content-template"}]
    sheets = SheetsClient()
    return [r for r in sheets.read_rows("EmailSubscribers")
            if r.get("Status", "").lower() != "unsubscribed"]

def _read_recent_articles():
    if settings.dry_run:
        return [{"Title": "Lead Gen Guide", "URL": "https://site.com/blog/lead-gen"},
                {"Title": "CRM Tools Review", "URL": "https://site.com/blog/crm-tools"}]
    sheets = SheetsClient()
    return sheets.read_rows("PublishedArticles")[:5]

def main():
    parser = argparse.ArgumentParser(description="Workflow 09: Email Marketing")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--mode", "-m", choices=["nurture", "newsletter"], default="nurture")
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    summary = run_pipeline(args.mode)
    print(f"\n[OK] Workflow 09 complete! Mode: {args.mode}")

if __name__ == "__main__": main()
