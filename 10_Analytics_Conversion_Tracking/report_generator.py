"""
10_Analytics_Conversion_Tracking/report_generator.py

Step 7 -- AI generates weekly/monthly performance reports.
"""
from __future__ import annotations
from typing import Any
from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("report_generator")

REPORT_SYSTEM_PROMPT = """\
You are a digital marketing analyst. Generate a weekly performance report.

Analyze:
1. TRAFFIC SUMMARY: sessions, organic %, week-over-week change
2. TOP PERFORMING PAGES: top 5 by traffic, top 5 by conversions
3. SEO RANKINGS: keywords moving up/down, new rankings
4. LEAD GENERATION: new leads, sources, avg score, conversion rate
5. EMAIL PERFORMANCE: open rate, click rate, trends
6. ANOMALIES: unusual spikes/drops (>20% change)
7. RECOMMENDATIONS: 3-5 specific actions

Return ONLY valid JSON:
{
  "summary": "...",
  "traffic": {"total": 0, "organic_pct": 0, "wow_change": "+5%"},
  "top_pages": [{"page": "...", "sessions": 0, "conversions": 0}],
  "seo_movers": {"up": [], "down": []},
  "leads": {"total": 0, "top_source": "...", "conversion_rate": "..."},
  "email": {"avg_open": "...", "avg_click": "..."},
  "anomalies": [],
  "recommendations": []
}
"""

def generate_report(analytics: dict, search: list, leads: dict,
                    emails: dict) -> dict[str, Any]:
    log.info("Generating performance report...")
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock report")
        return {
            "summary": "Solid week with 1,245 sessions (+8% WoW), 7 new leads, "
                       "and improving keyword rankings.",
            "traffic": {"total": 1245, "organic_pct": 65, "wow_change": "+8%"},
            "top_pages": [{"page": "/blog/lead-gen-guide", "sessions": 450, "conversions": 3}],
            "seo_movers": {
                "up": [{"keyword": "lead generation strategies", "from": 6, "to": 4.2}],
                "down": [{"keyword": "email marketing tips", "from": 9, "to": 11.3}],
            },
            "leads": {"total": 7, "top_source": "organic", "conversion_rate": "0.56%"},
            "email": {"avg_open": "44%", "avg_click": "15%"},
            "anomalies": ["Blog traffic up 23% -- likely from new CRM article ranking"],
            "recommendations": [
                "Create 2 more comparison posts (high conversion pattern)",
                "Update email-tips article (position dropped to 11.3)",
                "Add internal links from lead-gen-guide to CRM article",
            ],
        }
    data = (f"Analytics: {analytics}\nSearch Console: {search}\n"
            f"Leads: {leads}\nEmails: {emails}")
    return ask_ai_json(REPORT_SYSTEM_PROMPT, data)

def format_report_email(report: dict[str, Any]) -> str:
    """Format report into readable email body."""
    recs = "\n".join(f"  {i+1}. {r}" for i, r in enumerate(report.get("recommendations", [])))
    anomalies = "\n".join(f"  - {a}" for a in report.get("anomalies", []))
    traffic = report.get("traffic", {})
    leads = report.get("leads", {})
    return f"""
Weekly SEO & Lead Performance Report
======================================

SUMMARY: {report.get("summary", "")}

TRAFFIC:
  Sessions: {traffic.get("total", 0)} ({traffic.get("wow_change", "n/a")} WoW)
  Organic: {traffic.get("organic_pct", 0)}%

LEADS:
  New: {leads.get("total", 0)} | Top Source: {leads.get("top_source", "n/a")}
  Conversion Rate: {leads.get("conversion_rate", "n/a")}

ANOMALIES:
{anomalies or "  None detected"}

RECOMMENDATIONS:
{recs or "  None"}
======================================
"""
