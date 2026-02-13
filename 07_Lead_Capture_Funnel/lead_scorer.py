"""
07_Lead_Capture_Funnel/lead_scorer.py

Steps 4-5 -- AI lead enrichment and scoring.
"""
from __future__ import annotations
import re
from typing import Any
from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("lead_scorer")

DISPOSABLE_DOMAINS = {"mailinator.com", "guerrillamail.com", "tempmail.com", "throwaway.email",
                      "yopmail.com", "sharklasers.com", "guerrillamailblock.com"}

SCORING_SYSTEM_PROMPT = """\
Score this lead from 1-100 based on likelihood to convert.

Scoring Criteria:
- Business email domain (+20 vs free email like gmail)
- Company size SMB/Enterprise (+15 vs individual)
- Source is high-intent page like pricing/demo (+25 vs blog)
- Downloaded high-value lead magnet (+10)
- Industry match (+15)
- Has phone number (+5)

Return ONLY valid JSON:
{
  "score": 72,
  "tier": "warm",
  "reasoning": "...",
  "recommended_action": "...",
  "segment": "seo-interested-smb"
}

Tiers: 80-100=HOT, 50-79=WARM, 20-49=COOL, 0-19=LOW
"""

def validate_lead(lead: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate lead data: email format, disposable check."""
    issues = []
    email = lead.get("email", "")
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        issues.append("Invalid email format")
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in DISPOSABLE_DOMAINS:
        issues.append(f"Disposable email domain: {domain}")
    if not lead.get("name"):
        issues.append("Missing name")
    return len(issues) == 0, issues

def score_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """AI-powered lead scoring."""
    log.info("Scoring lead: %s (%s)", lead.get("name", "?"), lead.get("email", "?"))
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock lead score")
        email = lead.get("email", "")
        is_biz = "@gmail" not in email and "@yahoo" not in email
        score = 72 if is_biz else 35
        tier = "warm" if score >= 50 else "cool"
        return {"score": score, "tier": tier,
                "reasoning": f"{'Business' if is_biz else 'Free'} email domain",
                "recommended_action": "Add to nurture sequence",
                "segment": "seo-interested-smb" if is_biz else "general"}
    user_prompt = "\n".join(f"- {k}: {v}" for k, v in lead.items())
    return ask_ai_json(SCORING_SYSTEM_PROMPT, f"Lead Data:\n{user_prompt}")

def classify_tier(score: int) -> str:
    if score >= 80: return "hot"
    if score >= 50: return "warm"
    if score >= 20: return "cool"
    return "low"
