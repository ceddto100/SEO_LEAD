"""
08_CRM_AI_FollowUp/main.py

Orchestrator for Workflow 08: CRM + AI Follow-Up Engine.
Generates personalized follow-up email sequences based on lead tier.
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
from followup_engine import get_cadence, generate_followup_email

log = get_logger("workflow_08")

TRACKER_HEADERS = ["Lead Name", "Email", "Sequence Step", "Email Subject",
                   "Send Date", "Status"]

def run_pipeline(leads: list[dict[str, Any]]) -> dict[str, Any]:
    start = time.time()
    log.info("=" * 70)
    log.info("WORKFLOW 08: CRM + AI FOLLOW-UP ENGINE")
    log.info("=" * 70)

    sheets = SheetsClient()
    emails_generated = 0

    for i, lead in enumerate(leads, 1):
        name = lead.get("name", "Unknown")
        tier = lead.get("tier", "cool")
        log.info("LEAD %d/%d: %s (tier: %s)", i, len(leads), name, tier)

        cadence = get_cadence(tier)
        for step_idx, step in enumerate(cadence, 1):
            email = generate_followup_email(lead, step_idx, len(cadence), step["type"])
            send_date = (datetime.now() + timedelta(days=step["day"])).strftime("%Y-%m-%d")

            sheets.append_rows("FollowUpTracker", [{
                "Lead Name": name, "Email": lead.get("email", ""),
                "Sequence Step": f"{step_idx}/{len(cadence)}",
                "Email Subject": email.get("subject", ""),
                "Send Date": send_date, "Status": "scheduled",
            }], headers=TRACKER_HEADERS)
            emails_generated += 1

    elapsed = round(time.time() - start, 1)
    send_notification(
        subject=f"Follow-Up Sequences -- {emails_generated} emails scheduled",
        body=f"{len(leads)} leads, {emails_generated} emails queued, {elapsed}s")

    summary = {"leads": len(leads), "emails_generated": emails_generated,
               "elapsed_seconds": elapsed}
    log.info("WORKFLOW 08 COMPLETE: %d emails for %d leads", emails_generated, len(leads))
    return summary

def _read_leads():
    if settings.dry_run:
        return [
            {"name": "John Doe", "email": "john@acme.com", "company": "Acme Corp",
             "tier": "warm", "source": "blog-cta", "lead_magnet": "free-seo-checklist"},
            {"name": "Sarah Lee", "email": "sarah@enterprise.io", "company": "Enterprise Co",
             "tier": "hot", "source": "pricing-page", "lead_magnet": "free-consultation"},
        ]
    sheets = SheetsClient()
    return [r for r in sheets.read_rows("MasterLeadList")
            if r.get("Status", "").lower() in ("new", "nurturing")]

def main():
    parser = argparse.ArgumentParser(description="Workflow 08: CRM Follow-Up")
    parser.add_argument("--dry-run", "-d", action="store_true")
    args = parser.parse_args()
    if args.dry_run and not settings.dry_run:
        object.__setattr__(settings, "dry_run", True)
    leads = _read_leads()
    if not leads: print("No leads for follow-up."); return
    summary = run_pipeline(leads)
    print(f"\n[OK] Workflow 08 complete! {summary['emails_generated']} follow-up emails queued.")

if __name__ == "__main__": main()
