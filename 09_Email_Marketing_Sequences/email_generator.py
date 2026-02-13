"""
09_Email_Marketing_Sequences/email_generator.py

Steps 3-4 -- AI generates nurture email sequences and weekly newsletters.
"""
from __future__ import annotations
from typing import Any
from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("email_generator")

NURTURE_SEQUENCE = [
    {"day": 0, "type": "welcome", "desc": "Welcome + deliver lead magnet"},
    {"day": 3, "type": "educational", "desc": "Educational content"},
    {"day": 7, "type": "case_study", "desc": "Case study / social proof"},
    {"day": 10, "type": "mistakes", "desc": "Common mistakes to avoid"},
    {"day": 14, "type": "resource", "desc": "Free tool / template"},
    {"day": 21, "type": "pitch", "desc": "Soft pitch + CTA"},
]

NURTURE_SYSTEM_PROMPT = """\
Write a nurture email for a subscriber.

EMAIL RULES:
1. Subject line: 6-10 words, curiosity or benefit driven
2. Preview text: 40-90 chars
3. Body: 200-400 words max
4. Personal tone, helpful friend not marketer
5. One main idea per email
6. One clear CTA
7. P.S. line with bonus tip

Return ONLY valid JSON:
{"subject": "...", "preview_text": "...", "body_html": "<p>Hi {{first_name}},</p>...",
 "cta_text": "...", "cta_url": "...", "ps_line": "P.S. ..."}
"""

NEWSLETTER_SYSTEM_PROMPT = """\
Create a weekly newsletter from recently published articles.

NEWSLETTER FORMAT:
- Subject: engaging, max 50 chars
- Preview text: 60-90 chars
- Intro: 2-3 sentence personal note (50 words max)
- For each article: catchy hook + 2-sentence summary + read more link
- Tip of the Week: one actionable tip
- CTA: invite reply

Return ONLY valid JSON:
{"subject": "...", "preview_text": "...", "intro": "...",
 "articles": [{"hook": "...", "summary": "...", "url": "..."}],
 "tip_of_week": "...", "cta": "..."}
"""

def generate_nurture_email(subscriber: dict[str, Any], step_idx: int,
                           email_type: str) -> dict[str, Any]:
    log.info("Generating nurture email %d (%s) for %s",
             step_idx + 1, email_type, subscriber.get("name", "?"))
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock nurture email")
        name = subscriber.get("name", "there")
        return {
            "subject": f"Quick {email_type} tip for you",
            "preview_text": f"Hey {name}, I wanted to share something useful...",
            "body_html": f"<p>Hi {name},</p><p>Here's a quick {email_type} insight "
                         f"based on your interest in {subscriber.get('segment', 'marketing')}.</p>"
                         f"<p>Best,<br>Your Team</p>",
            "cta_text": "Read More", "cta_url": "https://yourdomain.com/blog",
            "ps_line": "P.S. Reply if you have any questions!",
        }
    return ask_ai_json(NURTURE_SYSTEM_PROMPT,
                       f"Subscriber: {subscriber.get('name')}\nSegment: {subscriber.get('segment')}\n"
                       f"Email #{step_idx + 1}/{len(NURTURE_SEQUENCE)}, Type: {email_type}\n"
                       f"Lead Magnet: {subscriber.get('lead_magnet', 'n/a')}")

def generate_newsletter(articles: list[dict[str, Any]]) -> dict[str, Any]:
    log.info("Generating newsletter from %d articles", len(articles))
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock newsletter")
        return {
            "subject": "This Week in Marketing",
            "preview_text": "Top articles and tips from this week",
            "intro": "Happy Thursday! Here's what we published this week.",
            "articles": [{"hook": a.get("Title", ""), "summary": "Great insights on this topic.",
                          "url": a.get("URL", "#")} for a in articles[:5]],
            "tip_of_week": "Track your keyword rankings weekly to spot trends early.",
            "cta": "Hit reply and tell me what topic you'd like covered next!",
        }
    article_text = "\n".join(f"- {a.get('Title', '')}: {a.get('URL', '')}" for a in articles)
    return ask_ai_json(NEWSLETTER_SYSTEM_PROMPT, f"ARTICLES:\n{article_text}")
