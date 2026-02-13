"""
07_Lead_Capture_Funnel/main.py

Orchestrator for Workflow 07: Lead Capture & Funnel Automation.
Validates leads, scores them with AI, routes by tier, saves to Sheets.
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
from lead_scorer import validate_lead, score_lead, classify_tier

log = get_logger("workflow_07")

LEAD_HEADERS = ["Name", "Email", "Phone", "Company", "Source", "Score", "Tier",
                "Segment", "Lead Magnet", "Date", "Status"]

def run_pipeline(leads: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 07: LEAD CAPTURE & FUNNEL AUTOMATION")
    log.info("=" * 70)
    log.info("Leads to process: %d", len(leads))

    sheets = SheetsClient()
    processed, rejected = [], []

    for i, lead in enumerate(leads, 1):
        name = lead.get("name", "Unknown")
        log.info("LEAD %d/%d: %s", i, len(leads), name)

        valid, issues = validate_lead(lead)
        if not valid:
            log.warning("  Rejected: %s", ", ".join(issues))
            rejected.append({"name": name, "issues": issues})
            continue

        scoring = score_lead(lead)
        tier = classify_tier(scoring.get("score", 0))

        row = {"Name": name, "Email": lead.get("email", ""),
               "Phone": lead.get("phone", ""), "Company": lead.get("company", ""),
               "Source": lead.get("source", ""), "Score": scoring.get("score", 0),
               "Tier": tier, "Segment": scoring.get("segment", ""),
               "Lead Magnet": lead.get("lead_magnet", ""),
               "Date": datetime.now().strftime("%Y-%m-%d"),
               "Status": "new" if tier in ("hot", "warm") else "passive"}
        sheets.append_rows("MasterLeadList", [row], headers=LEAD_HEADERS)
        processed.append({**row, "action": scoring.get("recommended_action", "")})
        log.info("  -> Score: %d, Tier: %s", scoring.get("score", 0), tier)

    elapsed = round(time.time() - start, 1)
    hot = sum(1 for p in processed if p.get("Tier") == "hot")
    send_notification(
        subject=f"Leads Processed -- {len(processed)} scored ({hot} hot)",
        body=f"Processed: {len(processed)}, Rejected: {len(rejected)}, Hot: {hot}, Time: {elapsed}s")

    summary = {"processed": len(processed), "rejected": len(rejected),
               "hot_leads": hot, "elapsed_seconds": elapsed}
    log.info("WORKFLOW 07 COMPLETE: %d processed, %d rejected", len(processed), len(rejected))
    return summary

def _read_leads():
    if settings.dry_run:
        return [
            {"name": "John Doe", "email": "john@acme.com", "company": "Acme Corp",
             "source": "blog-cta", "lead_magnet": "free-seo-checklist", "phone": "+1234567890"},
            {"name": "Jane Smith", "email": "jane@gmail.com", "company": "",
             "source": "newsletter", "lead_magnet": "content-template"},
            {"name": "Bad Lead", "email": "test@mailinator.com", "company": "",
             "source": "unknown", "lead_magnet": ""},
        ]
    # In production, leads come via webhook; this reads any unprocessed from Sheets
    sheets = SheetsClient()
    return sheets.read_rows("IncomingLeads")

def main():
    parser = argparse.ArgumentParser(description="Workflow 07: Lead Capture")
    parser.add_argument("--dry-run", "-d", action="store_true")
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    leads = _read_leads()
    if not leads: print("No leads to process."); return
    summary = run_pipeline(leads)
    print(f"\n[OK] Workflow 07 complete! {summary['processed']} leads processed.")

if __name__ == "__main__": main()
