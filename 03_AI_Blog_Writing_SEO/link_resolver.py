"""
03_AI_Blog_Writing_SEO/link_resolver.py

Step 7 from workflow.txt -- Resolve Internal Links.
Replaces [INTERNAL_LINK: anchor text -> slug] placeholders in the HTML
with actual <a href="..."> tags, looking up slugs from published articles.
"""

from __future__ import annotations

import re
from typing import Any

from shared.config import settings
from shared.google_sheets import SheetsClient
from shared.logger import get_logger

log = get_logger("link_resolver")

# Pattern to match: [INTERNAL_LINK: anchor text -> slug]
LINK_PATTERN = re.compile(
    r'\[INTERNAL_LINK:\s*(.+?)\s*->\s*(.+?)\s*\]',
    re.IGNORECASE,
)

# Base URL for blog links (override in .env if needed)
BLOG_BASE_URL = "/blog/"


def resolve_links(
    article_html: str,
    published_slugs: list[str] | None = None,
) -> tuple[str, int]:
    """
    Replace [INTERNAL_LINK: text -> slug] placeholders with HTML links.

    If published_slugs is provided, only resolves links whose slug exists
    in the published articles list. Otherwise resolves all links.

    Returns (resolved_html, link_count).
    """
    matches = LINK_PATTERN.findall(article_html)
    if not matches:
        log.info("No internal link placeholders found")
        return article_html, 0

    log.info("Found %d internal link placeholders", len(matches))

    # If no published slugs provided, try loading from Sheets
    if published_slugs is None:
        published_slugs = _load_published_slugs()

    resolved_count = 0
    result_html = article_html

    for anchor_text, slug in matches:
        slug_clean = slug.strip().lower()

        # Check if slug exists in published articles (if we have the list)
        if published_slugs and slug_clean not in published_slugs:
            log.info("  Slug '%s' not yet published, keeping placeholder", slug_clean)
            continue

        # Build the HTML link
        href = f"{BLOG_BASE_URL}{slug_clean}"
        link_html = f'<a href="{href}">{anchor_text.strip()}</a>'

        # Replace this specific placeholder
        placeholder = f"[INTERNAL_LINK: {anchor_text} -> {slug}]"
        result_html = result_html.replace(placeholder, link_html)
        resolved_count += 1
        log.info("  Resolved: '%s' -> %s", anchor_text.strip(), href)

    log.info("Resolved %d/%d internal links", resolved_count, len(matches))
    return result_html, resolved_count


def _load_published_slugs() -> list[str]:
    """
    Load published article slugs from the PublishedArticles sheet.
    """
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock published slugs")
        return [
            "digital-marketing-strategies",
            "lead-generation-guide",
            "email-marketing-tips",
            "seo-best-practices",
        ]

    try:
        sheets = SheetsClient()
        rows = sheets.read_rows("PublishedArticles")
        slugs = [r.get("Slug", "").lower() for r in rows if r.get("Slug")]
        log.info("Loaded %d published slugs", len(slugs))
        return slugs
    except Exception as e:
        log.warning("Could not load published slugs: %s", e)
        return []
