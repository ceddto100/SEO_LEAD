"""
01_Keyword_Market_Research/keyword_expander.py

Step 3 from workflow.txt — Calls DataForSEO API to get search volume,
competition, and CPC data for seed keywords.  Falls back to mock data
in dry-run mode.
"""

from __future__ import annotations

import base64
from typing import Any

import requests

from shared.config import settings
from shared.logger import get_logger

log = get_logger("keyword_expander")


# ── Public API ───────────────────────────────────────────────────────────────

def expand_keywords(
    seed_keywords: list[str],
    location_code: int | None = None,
    language_code: str | None = None,
) -> list[dict[str, Any]]:
    """
    Query DataForSEO for keyword metrics.

    Returns a list of dicts, each with:
        keyword, search_volume, competition, cpc
    """
    location_code = location_code or settings.seo_location_code
    language_code = language_code or settings.seo_language_code

    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock keyword data for: %s", seed_keywords)
        return _mock_keyword_data(seed_keywords)

    log.info("Querying DataForSEO for %d seed keywords…", len(seed_keywords))
    return _call_dataforseo_search_volume(seed_keywords, location_code, language_code)


def get_keyword_suggestions(
    seed_keywords: list[str],
    location_code: int | None = None,
    language_code: str | None = None,
) -> list[dict[str, Any]]:
    """
    Query DataForSEO for related keyword suggestions (keyword ideas).

    Returns additional keyword ideas beyond the seed list.
    """
    location_code = location_code or settings.seo_location_code
    language_code = language_code or settings.seo_language_code

    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock keyword suggestions")
        return _mock_suggestions(seed_keywords)

    log.info("Querying DataForSEO keyword suggestions for: %s", seed_keywords)
    return _call_dataforseo_suggestions(seed_keywords, location_code, language_code)


# ── DataForSEO API Calls ────────────────────────────────────────────────────

def _auth_header() -> dict[str, str]:
    """Build Basic auth header for DataForSEO."""
    token = base64.b64encode(
        f"{settings.dataforseo_login}:{settings.dataforseo_password}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _call_dataforseo_search_volume(
    keywords: list[str],
    location_code: int,
    language_code: str,
) -> list[dict[str, Any]]:
    """POST to DataForSEO search_volume/live endpoint."""
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"

    payload = [
        {
            "keywords": keywords,
            "location_code": location_code,
            "language_code": language_code,
        }
    ]

    try:
        resp = requests.post(url, json=payload, headers=_auth_header(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for task in data.get("tasks", []):
            for item in (task.get("result") or []):
                results.append({
                    "keyword": item.get("keyword", ""),
                    "search_volume": item.get("search_volume", 0),
                    "competition": item.get("competition", 0),
                    "competition_level": _competition_level(item.get("competition", 0)),
                    "cpc": item.get("cpc", 0),
                })

        log.info("DataForSEO returned %d keyword results", len(results))
        return results

    except requests.RequestException as exc:
        log.error("DataForSEO search_volume API error: %s", exc)
        raise


def _call_dataforseo_suggestions(
    keywords: list[str],
    location_code: int,
    language_code: str,
) -> list[dict[str, Any]]:
    """POST to DataForSEO keyword_suggestions/live endpoint."""
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/live"

    payload = [
        {
            "keywords": keywords,
            "location_code": location_code,
            "language_code": language_code,
        }
    ]

    try:
        resp = requests.post(url, json=payload, headers=_auth_header(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for task in data.get("tasks", []):
            for item in (task.get("result") or []):
                results.append({
                    "keyword": item.get("keyword", ""),
                    "search_volume": item.get("search_volume", 0),
                    "competition": item.get("competition", 0),
                    "competition_level": _competition_level(item.get("competition", 0)),
                    "cpc": item.get("cpc", 0),
                })

        log.info("DataForSEO returned %d keyword suggestions", len(results))
        return results

    except requests.RequestException as exc:
        log.error("DataForSEO suggestions API error: %s", exc)
        raise


def _competition_level(comp: float) -> str:
    """Convert numeric competition (0-1) to label."""
    if comp < 0.33:
        return "low"
    elif comp < 0.66:
        return "medium"
    return "high"


# ── Mock Data ────────────────────────────────────────────────────────────────

def _mock_keyword_data(seed_keywords: list[str]) -> list[dict[str, Any]]:
    """Generate realistic-looking mock data for dry-run testing."""
    mock_metrics = [
        (2400, 0.34, 4.50), (8100, 0.67, 3.20), (1900, 0.22, 5.10),
        (5600, 0.55, 2.80), (3300, 0.41, 3.90), (720, 0.18, 6.20),
    ]
    results = []
    for i, kw in enumerate(seed_keywords):
        vol, comp, cpc = mock_metrics[i % len(mock_metrics)]
        results.append({
            "keyword": kw,
            "search_volume": vol,
            "competition": comp,
            "competition_level": _competition_level(comp),
            "cpc": cpc,
        })
    return results


def _mock_suggestions(seed_keywords: list[str]) -> list[dict[str, Any]]:
    """Mock keyword suggestions for dry-run."""
    suffix_ideas = [
        "for small business", "tools", "strategies 2026", "best practices",
        "software", "guide", "tips", "examples", "vs competitors", "free",
    ]
    results = []
    for kw in seed_keywords[:3]:
        for suffix in suffix_ideas:
            results.append({
                "keyword": f"{kw} {suffix}",
                "search_volume": 500,
                "competition": 0.30,
                "competition_level": "low",
                "cpc": 2.50,
            })
    return results
