"""
08_CRM_AI_FollowUp/followup_engine.py

Steps 2-3 -- Determine follow-up cadence and generate AI personalized emails.
"""
from __future__ import annotations
from typing import Any
from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("followup_engine")

CADENCES = {
    "hot":  [{"day": 0, "type": "personalized_email"}, {"day": 1, "type": "value_add_email"},
             {"day": 3, "type": "case_study_email"}, {"day": 7, "type": "last_chance_email"}],
    "warm": [{"day": 1, "type": "personalized_email"}, {"day": 3, "type": "value_add_email"},
             {"day": 7, "type": "case_study_email"}, {"day": 14, "type": "last_chance_email"}],
    "cool": [{"day": 3, "type": "personalized_email"}, {"day": 7, "type": "value_add_email"},
             {"day": 14, "type": "case_study_email"}, {"day": 30, "type": "last_chance_email"}],
}

EMAIL_SYSTEM_PROMPT = """\
You are a sales development rep writing a follow-up email.

WRITING RULES:
1. Keep it under 150 words
2. Personalize based on their company/industry
3. Reference what they downloaded or read
4. Provide genuine value (tip, insight, resource)
5. One clear CTA (reply, book a call, read resource)
6. NO pushy sales language
7. Write like a real human
8. Subject line: short, curiosity-driven, no spam triggers

Return ONLY valid JSON:
{"subject": "...", "body": "...", "cta_type": "reply", "cta_link": ""}
"""

def get_cadence(tier: str) -> list[dict[str, Any]]:
    return CADENCES.get(tier, CADENCES["cool"])

def generate_followup_email(lead: dict[str, Any], step: int, total: int,
                            email_type: str) -> dict[str, Any]:
    log.info("Generating %s for %s (step %d/%d)", email_type, lead.get("name", "?"), step, total)
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock follow-up email")
        name = lead.get("name", "there")
        return {
            "subject": f"Quick tip for {lead.get('company', 'your team')}",
            "body": f"Hi {name},\n\nI noticed you downloaded our "
                    f"{lead.get('lead_magnet', 'resource')}. Here's a quick tip...\n\n"
                    f"Would love to hear how it's working for you.\n\nBest,\nYour Name",
            "cta_type": "reply",
            "cta_link": "",
        }
    user_prompt = (f"Lead: {lead.get('name')} at {lead.get('company')}\n"
                   f"Tier: {lead.get('tier')}\nSource: {lead.get('source')}\n"
                   f"Lead Magnet: {lead.get('lead_magnet')}\n"
                   f"Step {step}/{total}, Type: {email_type}")
    return ask_ai_json(EMAIL_SYSTEM_PROMPT, user_prompt)
