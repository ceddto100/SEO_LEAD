"""
01_Keyword_Market_Research/competitor_analysis.py

Steps 5-6 from workflow.txt — Two-phase competitor analysis:
  Phase 1: Call DataForSEO SERP API for top 10 results for each primary keyword
  Phase 2: Send SERP results to AI for gap analysis
"""

from __future__ import annotations

import base64
import json
from typing import Any

import requests

from shared.ai_client import ask_ai_json
from shared.config import settings
from shared.logger import get_logger

log = get_logger("competitor_analysis")


# ── Prompt Templates ─────────────────────────────────────────────────────────

COMPETITOR_SYSTEM_PROMPT = """\
You are an expert SEO competitor analyst. You analyze SERP data to identify \
content gaps and strategic opportunities. Always return valid JSON — no \
commentary outside the JSON object.\
"""

COMPETITOR_USER_PROMPT = """\
Analyze these top 10 SERP results for "{keyword}":

{serp_results_json}

**Identify:**
1. **Content gaps** — topics the top-ranking pages are NOT covering well
2. **Weak content** — thin, outdated, or low-quality pages you could outrank
3. **Content format opportunities** — formats missing from the SERP (listicles, \
comparison tables, video guides, interactive tools, infographics)
4. **Recommended angles** — unique angles for new content that would stand out

**Return exactly this JSON structure:**
{{
  "keyword": "{keyword}",
  "gaps": ["topic 1 not covered", "topic 2 not covered"],
  "weak_competitors": [
    {{"url": "https://...", "title": "...", "weakness": "Thin content, only 500 words"}}
  ],
  "format_opportunities": ["comparison table", "video walkthrough"],
  "recommended_angles": [
    "Focus on 2026 data that competitors haven't updated",
    "Include expert quotes and case studies"
  ],
  "difficulty_assessment": "medium",
  "estimated_ranking_time": "3-6 months"
}}
"""


# ── Public API ───────────────────────────────────────────────────────────────

def analyze_competitors(
    primary_keywords: list[str],
    location_code: int | None = None,
    language_code: str | None = None,
) -> list[dict[str, Any]]:
    """
    Run full competitor analysis for a list of primary keywords.

    For each keyword:
      1. Pulls top 10 SERP results from DataForSEO
      2. Sends to AI for gap analysis

    Returns a list of analysis dicts (one per keyword).
    """
    location_code = location_code or settings.seo_location_code
    language_code = language_code or settings.seo_language_code

    results = []
    for keyword in primary_keywords:
        log.info("Analyzing competitors for: '%s'", keyword)

        # Phase 1: Get SERP data
        serp_data = _get_serp_results(keyword, location_code, language_code)

        # Phase 2: AI analysis
        analysis = _ai_gap_analysis(keyword, serp_data)
        results.append(analysis)

    log.info("Completed competitor analysis for %d keywords", len(results))
    return results


def flatten_competitor_gaps(analyses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Flatten competitor analyses into rows suitable for Google Sheets.

    Returns one row per gap/opportunity.
    """
    rows = []
    for analysis in analyses:
        keyword = analysis.get("keyword", "")
        difficulty = analysis.get("difficulty_assessment", "")
        est_time = analysis.get("estimated_ranking_time", "")

        # Content gaps
        for gap in analysis.get("gaps", []):
            rows.append({
                "Keyword": keyword,
                "Type": "content_gap",
                "Detail": gap,
                "Difficulty": difficulty,
                "Est. Ranking Time": est_time,
            })

        # Format opportunities
        for fmt in analysis.get("format_opportunities", []):
            rows.append({
                "Keyword": keyword,
                "Type": "format_opportunity",
                "Detail": fmt,
                "Difficulty": difficulty,
                "Est. Ranking Time": est_time,
            })

        # Recommended angles
        for angle in analysis.get("recommended_angles", []):
            rows.append({
                "Keyword": keyword,
                "Type": "recommended_angle",
                "Detail": angle,
                "Difficulty": difficulty,
                "Est. Ranking Time": est_time,
            })

        # Weak competitors
        for weak in analysis.get("weak_competitors", []):
            rows.append({
                "Keyword": keyword,
                "Type": "weak_competitor",
                "Detail": f"{weak.get('url', '')} — {weak.get('weakness', '')}",
                "Difficulty": difficulty,
                "Est. Ranking Time": est_time,
            })

    log.info("Flattened %d competitor gap rows", len(rows))
    return rows


# ── DataForSEO SERP API ─────────────────────────────────────────────────────

def _auth_header() -> dict[str, str]:
    token = base64.b64encode(
        f"{settings.dataforseo_login}:{settings.dataforseo_password}".encode()
    ).decode()
    return {
        "Authorization": f"Basic {token}",
        "Content-Type": "application/json",
    }


def _get_serp_results(
    keyword: str,
    location_code: int,
    language_code: str,
) -> list[dict[str, Any]]:
    """Fetch top 10 organic SERP results from DataForSEO."""
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock SERP data for '%s'", keyword)
        return _mock_serp_data(keyword)

    url = "https://api.dataforseo.com/v3/serp/google/organic/live/regular"
    payload = [
        {
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": 10,
        }
    ]

    try:
        resp = requests.post(url, json=payload, headers=_auth_header(), timeout=30)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for task in data.get("tasks", []):
            for result_item in (task.get("result") or []):
                for item in (result_item.get("items") or []):
                    if item.get("type") == "organic":
                        results.append({
                            "position": item.get("rank_absolute", 0),
                            "url": item.get("url", ""),
                            "title": item.get("title", ""),
                            "description": item.get("description", ""),
                            "domain": item.get("domain", ""),
                        })

        log.info("SERP returned %d organic results for '%s'", len(results), keyword)
        return results[:10]

    except requests.RequestException as exc:
        log.error("DataForSEO SERP API error for '%s': %s", keyword, exc)
        raise


# ── AI Gap Analysis ──────────────────────────────────────────────────────────

def _ai_gap_analysis(
    keyword: str,
    serp_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """Send SERP data to AI for competitive gap analysis."""
    log.info("Running AI gap analysis for '%s' (%d SERP results)", keyword, len(serp_data))

    serp_json = json.dumps(serp_data, indent=2)
    user_prompt = COMPETITOR_USER_PROMPT.format(
        keyword=keyword,
        serp_results_json=serp_json,
    )

    result = ask_ai_json(COMPETITOR_SYSTEM_PROMPT, user_prompt, temperature=0.5)

    # Ensure keyword is in the result
    if isinstance(result, dict):
        result["keyword"] = keyword

    return result


# ── Mock Data ────────────────────────────────────────────────────────────────

def _mock_serp_data(keyword: str) -> list[dict[str, Any]]:
    """Generate mock SERP data for dry-run testing."""
    domains = [
        "hubspot.com", "salesforce.com", "blog.hootsuite.com",
        "neilpatel.com", "semrush.com", "ahrefs.com",
        "backlinko.com", "moz.com", "searchenginejournal.com",
        "contentmarketinginstitute.com",
    ]
    return [
        {
            "position": i + 1,
            "url": f"https://{domain}/blog/{keyword.replace(' ', '-')}",
            "title": f"{keyword.title()} — {domain.split('.')[0].title()} Guide ({2025 + (i % 2)})",
            "description": f"Learn about {keyword} with this comprehensive guide from {domain}.",
            "domain": domain,
        }
        for i, domain in enumerate(domains)
    ]
