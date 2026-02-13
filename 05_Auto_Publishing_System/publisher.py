"""
05_Auto_Publishing_System/publisher.py

Steps 2-6 -- Validate, format, and publish articles to WordPress/Blogger/Webflow.
"""
from __future__ import annotations
import json, requests
from typing import Any
from shared.config import settings
from shared.logger import get_logger

log = get_logger("publisher")

def validate_article(article: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate article completeness before publishing."""
    issues = []
    if not article.get("Title"): issues.append("Missing title")
    if not article.get("Slug"): issues.append("Missing slug")
    if not article.get("Meta Title"): issues.append("Missing meta title")
    if not article.get("Meta Description"): issues.append("Missing meta description")
    passed = len(issues) == 0
    log.info("Validation %s: %s", "PASSED" if passed else "FAILED", article.get("Title", "?"))
    if issues: log.warning("  Issues: %s", ", ".join(issues))
    return passed, issues

def format_for_wordpress(html: str, meta: dict[str, Any]) -> dict[str, Any]:
    """Format article for WordPress REST API."""
    return {
        "title": meta.get("meta_title", meta.get("Title", "")),
        "content": html,
        "slug": meta.get("slug", meta.get("Slug", "")),
        "status": "publish",
        "meta": {
            "_yoast_wpseo_metadesc": meta.get("meta_description", meta.get("Meta Description", "")),
            "_yoast_wpseo_focuskw": meta.get("focus_keyword", meta.get("Keyword", "")),
        },
    }

def publish_to_wordpress(wp_data: dict[str, Any]) -> dict[str, Any]:
    """Publish to WordPress via REST API."""
    log.info("Publishing to WordPress: '%s'", wp_data.get("title", ""))
    if settings.dry_run:
        log.info("[DRY-RUN] Skipping WordPress publish")
        slug = wp_data.get("slug", "untitled")
        return {"id": 12345, "link": f"https://yourdomain.com/blog/{slug}",
                "slug": slug, "status": "publish"}
    endpoint = f"{settings.wordpress_url}/wp-json/wp/v2/posts"
    headers = {"Authorization": f"Bearer {settings.wordpress_token}",
               "Content-Type": "application/json"}
    resp = requests.post(endpoint, json=wp_data, headers=headers, timeout=30)
    resp.raise_for_status()
    result = resp.json()
    log.info("Published: %s", result.get("link", ""))
    return result

def submit_to_google_indexing(url: str) -> bool:
    """Submit URL to Google Indexing API for fast crawling."""
    log.info("Submitting to Google Indexing: %s", url)
    if settings.dry_run:
        log.info("[DRY-RUN] Skipping Google Indexing API")
        return True
    endpoint = "https://indexing.googleapis.com/v3/urlNotifications:publish"
    body = {"url": url, "type": "URL_UPDATED"}
    try:
        resp = requests.post(endpoint, json=body, timeout=15)
        resp.raise_for_status()
        log.info("Indexing submitted successfully")
        return True
    except Exception as e:
        log.warning("Indexing submission failed: %s", e)
        return False
