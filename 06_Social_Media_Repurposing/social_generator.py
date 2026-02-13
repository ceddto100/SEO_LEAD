"""
06_Social_Media_Repurposing/social_generator.py

Step 3 -- AI generates platform-specific social media posts from a blog article.
"""
from __future__ import annotations
from typing import Any
from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("social_generator")

SOCIAL_SYSTEM_PROMPT = """\
You are a social media content expert. Repurpose a blog article into posts
for multiple platforms.

Create:
1. TWITTER/X THREAD (5-7 tweets, 280 chars each, hashtags on last tweet only)
2. LINKEDIN POST (1200-1500 chars, professional tone, 3-5 hashtags)
3. INSTAGRAM CAPTION (500-800 chars, 15-20 hashtags, emojis)
4. FACEBOOK POST (300-500 chars, conversational, include link)
5. PINTEREST PIN DESCRIPTION (200-300 chars, SEO keywords)

Return ONLY valid JSON:
{
  "twitter_thread": ["tweet1", "tweet2", ...],
  "linkedin": "full post",
  "instagram": {"caption": "...", "hashtags": "#tag1 #tag2"},
  "facebook": "full post",
  "pinterest": "pin description"
}
"""

def generate_social_content(title: str, url: str, keyword: str,
                            excerpt: str) -> dict[str, Any]:
    log.info("Generating social content for: '%s'", title)
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock social content")
        return _mock_social(title, url, keyword)
    return ask_ai_json(SOCIAL_SYSTEM_PROMPT,
                       f"Title: {title}\nURL: {url}\nKeyword: {keyword}\nExcerpt: {excerpt}")

def _mock_social(title: str, url: str, keyword: str) -> dict[str, Any]:
    return {
        "twitter_thread": [
            f"Most businesses get {keyword} completely wrong. Here's what actually works (thread):",
            f"1/ The biggest mistake? Not having a strategy. {keyword} requires a systematic approach.",
            f"2/ Start with research. Understand your audience, their pain points, and search behavior.",
            f"3/ Create content that solves real problems. Not fluff -- actionable, data-backed insights.",
            f"4/ Consistency beats perfection. Publish regularly and optimize based on data.",
            f"5/ The full breakdown is in our new guide. Read it here: {url} #Marketing #{keyword.replace(' ', '')}",
        ],
        "linkedin": f"I just published a comprehensive guide on {keyword}.\n\n"
                    f"Here are the key takeaways:\n\n"
                    f"- Strategy matters more than tactics\n"
                    f"- Data-driven decisions win every time\n"
                    f"- Consistency compounds over time\n\n"
                    f"Read the full guide: {url}\n\n"
                    f"#Marketing #SEO #{keyword.replace(' ', '')}",
        "instagram": {
            "caption": f"New guide alert! Everything you need to know about {keyword}. "
                       f"Link in bio for the full breakdown.",
            "hashtags": f"#{keyword.replace(' ', '')} #marketing #seo #digitalmarketing "
                        f"#contentmarketing #growthhacking #business",
        },
        "facebook": f"Just dropped our comprehensive guide to {keyword}. "
                    f"If you're looking to level up your strategy, this one's for you: {url}",
        "pinterest": f"Complete guide to {keyword} - strategies, tools, and best practices "
                     f"for growing your business in 2026.",
    }
