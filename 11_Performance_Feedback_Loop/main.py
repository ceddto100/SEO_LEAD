"""
11_Performance_Feedback_Loop/main.py

Orchestrator for Workflow 11: Performance Feedback Loop.
Analyzes performance data, triggers content refreshes, feeds new keywords
back to Workflow 01, and updates strategy rules.
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
from optimizer import analyze_performance, build_refresh_brief

log = get_logger("workflow_11")

OPT_LOG_HEADERS = ["Date", "Action Type", "Target", "Issue", "Action Taken", "Expected Impact"]

def run_pipeline() -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 11: PERFORMANCE FEEDBACK LOOP")
    log.info("=" * 70)

    sheets = SheetsClient()
    today = datetime.now().strftime("%Y-%m-%d")

    # Step 1: Read performance data
    perf_data = _read_performance_data()

    # Step 2: AI analysis
    analysis = analyze_performance(perf_data)

    actions_taken = 0

    # Step 3: Queue content refreshes
    for page in analysis.get("refresh_candidates", []):
        brief = build_refresh_brief(page)
        sheets.append_rows("ContentCalendar", [{
            "Title": f"[REFRESH] {page.get('url', '')}",
            "Keyword": page.get("keyword", ""),
            "Type": "refresh", "Status": "planned", "Priority": "1",
            "Publish Date": today,
        }])
        sheets.append_rows("OptimizationLog", [{
            "Date": today, "Action Type": "Content Refresh",
            "Target": page.get("url", ""), "Issue": page.get("decline", ""),
            "Action Taken": "; ".join(page.get("actions", [])),
            "Expected Impact": "Recover lost traffic",
        }], headers=OPT_LOG_HEADERS)
        actions_taken += 1
        log.info("Queued refresh: %s", page.get("url", ""))

    # Step 4: Feed new keywords to ContentQueue
    new_kws = analysis.get("keyword_adjustments", {}).get("new_targets", [])
    for kw in new_kws:
        sheets.append_rows("ContentQueue", [{
            "Keyword": kw, "Status": "new", "Source": "feedback-loop",
            "Date": today,
        }])
        actions_taken += 1
    if new_kws:
        log.info("Queued %d new keywords: %s", len(new_kws), ", ".join(new_kws))

    # Step 5: Log underperformer fixes
    for fix in analysis.get("underperformer_fixes", []):
        sheets.append_rows("OptimizationLog", [{
            "Date": today, "Action Type": "Underperformer Fix",
            "Target": fix.get("url", ""), "Issue": "; ".join(fix.get("issues", [])),
            "Action Taken": "; ".join(fix.get("actions", [])),
            "Expected Impact": "Improve rankings",
        }], headers=OPT_LOG_HEADERS)
        actions_taken += 1

    elapsed = round(time.time() - start, 1)
    insights = analysis.get("top_performer_insights", {})
    send_notification(
        subject=f"Feedback Loop Complete -- {actions_taken} actions queued",
        body=f"Actions: {actions_taken}\nNew Keywords: {len(new_kws)}\n"
             f"Refresh Candidates: {len(analysis.get('refresh_candidates', []))}\n"
             f"Patterns: {', '.join(insights.get('patterns', []))}\n"
             f"Time: {elapsed}s")

    summary = {"actions_taken": actions_taken, "new_keywords": len(new_kws),
               "refreshes_queued": len(analysis.get("refresh_candidates", [])),
               "elapsed_seconds": elapsed}
    log.info("WORKFLOW 11 COMPLETE: %d actions", actions_taken)
    return summary

def _read_performance_data():
    if settings.dry_run:
        return {
            "top_pages": [{"url": "/blog/lead-gen-guide", "sessions": 450,
                          "leads": 12, "conv_rate": "2.7%"}],
            "underperforming": [{"url": "/blog/seo-tips", "sessions": 23,
                                "expected": 200, "position": 34}],
            "keyword_opportunities": [{"keyword": "crm comparison", "position": 11,
                                      "impressions": 5000}],
            "declining_pages": [{"url": "/blog/email-tools", "prev_sessions": 300,
                                "curr_sessions": 150, "change": "-50%"}],
        }
    sheets = SheetsClient()
    return {"raw_metrics": sheets.read_rows("DailyMetrics"),
            "rankings": sheets.read_rows("KeywordRankings")}

def main():
    parser = argparse.ArgumentParser(description="Workflow 11: Feedback Loop")
    parser.add_argument("--dry-run", "-d", action="store_true")
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    summary = run_pipeline()
    print(f"\n[OK] Workflow 11 complete! {summary['actions_taken']} optimization actions queued.")

if __name__ == "__main__": main()
