"""
10_Analytics_Conversion_Tracking/main.py

Orchestrator for Workflow 10: Analytics + Conversion Tracking.
Pulls data from GA4, Search Console, Sheets; generates AI reports.
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
from data_collector import (pull_analytics_data, pull_search_console_data,
                            pull_lead_data, pull_email_data)
from report_generator import generate_report, format_report_email

log = get_logger("workflow_10")

METRICS_HEADERS = ["Date", "Sessions", "Users", "Organic", "Leads",
                   "Lead Avg Score", "Bounce%", "Conversions"]
RANKINGS_HEADERS = ["Date", "Keyword", "Impressions", "Clicks", "CTR",
                    "Position", "Page URL"]

def run_pipeline(mode: str = "daily") -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 10: ANALYTICS + CONVERSION TRACKING (mode: %s)", mode)
    log.info("=" * 70)

    sheets = SheetsClient()
    today = datetime.now().strftime("%Y-%m-%d")

    # Step 1-4: Pull all data
    analytics = pull_analytics_data()
    search_data = pull_search_console_data()
    lead_data = pull_lead_data()
    email_data = pull_email_data()

    # Step 5: Store daily metrics
    sheets.append_rows("DailyMetrics", [{
        "Date": today, "Sessions": analytics.get("sessions", 0),
        "Users": analytics.get("users", 0),
        "Organic": sum(s.get("sessions", 0) for s in analytics.get("sources", [])
                       if s.get("medium") == "organic"),
        "Leads": lead_data.get("new_leads", 0),
        "Lead Avg Score": lead_data.get("avg_score", 0),
        "Bounce%": f"{analytics.get('bounce_rate', 0):.0%}",
        "Conversions": analytics.get("conversions", 0),
    }], headers=METRICS_HEADERS)

    # Step 6: Store keyword rankings
    ranking_rows = [{"Date": today, "Keyword": kw.get("keyword", ""),
                     "Impressions": kw.get("impressions", 0), "Clicks": kw.get("clicks", 0),
                     "CTR": f"{kw.get('ctr', 0):.1%}", "Position": kw.get("position", 0),
                     "Page URL": kw.get("page", "")} for kw in search_data]
    if ranking_rows:
        sheets.append_rows("KeywordRankings", ranking_rows, headers=RANKINGS_HEADERS)

    result = {"metrics_stored": True, "keywords_tracked": len(search_data)}

    # Step 7: Generate report (weekly/monthly mode)
    if mode in ("weekly", "monthly"):
        report = generate_report(analytics, search_data, lead_data, email_data)
        report_text = format_report_email(report)
        send_notification(
            subject=f"{mode.title()} Report | {analytics.get('sessions', 0)} sessions, "
                    f"{lead_data.get('new_leads', 0)} leads",
            body=report_text)
        result["report_generated"] = True
        result["recommendations"] = report.get("recommendations", [])

    elapsed = round(time.time() - start, 1)
    result["elapsed_seconds"] = elapsed
    log.info("WORKFLOW 10 COMPLETE: %s", mode)
    return result

def main():
    parser = argparse.ArgumentParser(description="Workflow 10: Analytics")
    parser.add_argument("--dry-run", "-d", action="store_true")
    parser.add_argument("--mode", "-m", choices=["daily", "weekly", "monthly"], default="daily")
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    summary = run_pipeline(args.mode)
    print(f"\n[OK] Workflow 10 complete! Mode: {args.mode}")

if __name__ == "__main__": main()
