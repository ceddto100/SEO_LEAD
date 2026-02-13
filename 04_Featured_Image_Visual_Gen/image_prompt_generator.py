"""
04_Featured_Image_Visual_Gen/image_prompt_generator.py

Step 2 -- AI generates image prompts for DALL-E based on article data.
"""
from __future__ import annotations
from typing import Any
from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("image_prompt_gen")

PROMPT_SYSTEM = """\
Generate image prompts for an AI image generator (DALL-E 3).

Given a blog article's title and keyword, create prompts for:
1. Featured Image (1792x1024): Blog hero, no text on image, professional
2. Social Thumbnail (1024x1024): Eye-catching, Instagram/LinkedIn ready
3. Pinterest Pin (1024x1792): Vertical, with space for title overlay

Brand style: modern, clean, professional, blue/white color scheme.

Return ONLY valid JSON:
{
  "featured_prompt": "detailed prompt...",
  "social_prompt": "detailed prompt...",
  "pinterest_prompt": "detailed prompt...",
  "alt_text": "SEO-optimized alt text including keyword",
  "file_name": "keyword-slug-featured.png"
}
"""

def generate_image_prompts(title: str, keyword: str, content_type: str) -> dict[str, Any]:
    log.info("Generating image prompts for: '%s'", title)
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock image prompts")
        slug = keyword.lower().replace(" ", "-")
        return {
            "featured_prompt": f"Professional, modern illustration representing {keyword}, "
                               f"clean blue and white color scheme, no text, corporate style",
            "social_prompt": f"Eye-catching square graphic about {keyword}, "
                             f"modern minimalist design, vibrant blue tones",
            "pinterest_prompt": f"Vertical infographic style image about {keyword}, "
                                f"space for title overlay at top, professional design",
            "alt_text": f"{title} - comprehensive guide to {keyword}",
            "file_name": f"{slug}-featured.png",
        }
    return ask_ai_json(PROMPT_SYSTEM, f"Title: {title}\nKeyword: {keyword}\nType: {content_type}")
