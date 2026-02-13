"""
03_AI_Blog_Writing_SEO/seo_optimizer.py

Steps 4-6 from workflow.txt -- SEO Meta Generation + Quality Audit.
  - Generates meta title, description, schema markup, OG/Twitter tags
  - Runs an SEO quality audit scoring 12 factors
  - Returns pass/fail with recommendations
"""

from __future__ import annotations

import json
from typing import Any

from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("seo_optimizer")

# Minimum SEO score to pass (below this triggers a rewrite)
SEO_SCORE_THRESHOLD = 70

# ---------------------------------------------------------------------------
# Meta generation prompt
# ---------------------------------------------------------------------------

META_SYSTEM_PROMPT = """\
You are an SEO metadata specialist. Generate complete SEO metadata for the
given article.

Return ONLY valid JSON:
{
  "meta_title": "... (max 60 chars, include primary keyword)",
  "meta_description": "... (max 155 chars, include keyword, add CTA)",
  "slug": "keyword-optimized-slug",
  "focus_keyword": "the primary keyword",
  "secondary_keywords": ["kw1", "kw2", "kw3"],
  "schema_markup": {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": "...",
    "description": "...",
    "author": {"@type": "Person", "name": "Your Brand"},
    "datePublished": "YYYY-MM-DD",
    "image": ""
  },
  "og_title": "...",
  "og_description": "...",
  "twitter_title": "...",
  "twitter_description": "..."
}
"""

# ---------------------------------------------------------------------------
# SEO audit prompt
# ---------------------------------------------------------------------------

AUDIT_SYSTEM_PROMPT = """\
You are an SEO auditor. Review this article for SEO quality.

Check and score (1-10) each factor:
1. Keyword in H1 title
2. Keyword in first 100 words
3. Keyword density (1-2%)
4. H2/H3 structure and keyword usage
5. Internal link placeholders present
6. Image placeholders present
7. FAQ section present
8. CTA placements present
9. Meta title length (50-60 chars)
10. Meta description length (120-155 chars)
11. Readability (short paragraphs, lists)
12. Word count meets target

Return ONLY valid JSON:
{
  "overall_score": 85,
  "checks": [
    {"factor": "Keyword in H1", "score": 10, "pass": true, "note": ""},
    {"factor": "Keyword density", "score": 7, "pass": true, "note": "1.4% - good"}
  ],
  "issues": ["List of issues found"],
  "recommendations": ["List of improvement suggestions"]
}
"""


def generate_meta(
    title: str,
    keyword: str,
    publish_date: str,
) -> dict[str, Any]:
    """
    Generate SEO metadata for an article.
    """
    log.info("Generating SEO meta for: '%s'", title)

    if settings.dry_run:
        log.info("[DRY-RUN] Generating mock SEO meta")
        return _mock_meta(title, keyword, publish_date)

    user_prompt = (
        f"Title: {title}\n"
        f"Primary Keyword: {keyword}\n"
        f"Publish Date: {publish_date}\n"
    )

    result = ask_ai_json(META_SYSTEM_PROMPT, user_prompt)

    if not isinstance(result, dict):
        result = {"meta_title": title, "slug": keyword.lower().replace(" ", "-")}

    log.info("Meta generated: title=%s, slug=%s",
             result.get("meta_title", "")[:50],
             result.get("slug", ""))

    return result


def audit_seo(
    article_html: str,
    meta_data: dict[str, Any],
    target_word_count: int,
) -> dict[str, Any]:
    """
    Run an AI-powered SEO quality audit on the article.

    Returns audit results with overall_score, checks, issues,
    and recommendations.
    """
    log.info("Running SEO audit...")

    if settings.dry_run:
        log.info("[DRY-RUN] Generating mock SEO audit")
        return _mock_audit()

    meta_json = json.dumps(meta_data, indent=2)

    user_prompt = (
        f"ARTICLE HTML:\n{article_html[:6000]}\n\n"  # Truncate to fit context
        f"META DATA:\n{meta_json}\n\n"
        f"TARGET WORD COUNT: {target_word_count}\n"
    )

    result = ask_ai_json(AUDIT_SYSTEM_PROMPT, user_prompt)

    if not isinstance(result, dict):
        result = {"overall_score": 0, "checks": [], "issues": ["Audit failed"]}

    score = result.get("overall_score", 0)
    issues = result.get("issues", [])
    log.info("SEO audit score: %d/100 (%d issues)", score, len(issues))

    return result


def needs_rewrite(audit_result: dict[str, Any]) -> bool:
    """Check if the article needs a rewrite based on audit score."""
    score = audit_result.get("overall_score", 0)
    return score < SEO_SCORE_THRESHOLD


def format_audit_feedback(audit_result: dict[str, Any]) -> str:
    """
    Convert audit results into feedback string for the rewrite prompt.
    """
    lines = [f"SEO Score: {audit_result.get('overall_score', 0)}/100\n"]

    issues = audit_result.get("issues", [])
    if issues:
        lines.append("ISSUES TO FIX:")
        for issue in issues:
            lines.append(f"  - {issue}")

    recs = audit_result.get("recommendations", [])
    if recs:
        lines.append("\nRECOMMENDATIONS:")
        for rec in recs:
            lines.append(f"  - {rec}")

    failed = [c for c in audit_result.get("checks", []) if not c.get("pass", True)]
    if failed:
        lines.append("\nFAILED CHECKS:")
        for check in failed:
            lines.append(f"  - {check.get('factor', '?')}: {check.get('note', '')}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mock data for dry-run
# ---------------------------------------------------------------------------

def _mock_meta(title: str, keyword: str, publish_date: str) -> dict[str, Any]:
    slug = keyword.lower().replace(" ", "-")
    return {
        "meta_title": f"{title[:50]} | Your Brand",
        "meta_description": f"Discover the best {keyword} strategies for 2026. "
                            f"Actionable tips and expert insights. Get started now.",
        "slug": slug,
        "focus_keyword": keyword,
        "secondary_keywords": [
            f"best {keyword}",
            f"{keyword} tips",
            f"{keyword} guide",
        ],
        "schema_markup": {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": title,
            "description": f"Complete guide to {keyword}",
            "author": {"@type": "Person", "name": "Your Brand"},
            "datePublished": publish_date,
            "image": "",
        },
        "og_title": title,
        "og_description": f"Learn everything about {keyword} in our comprehensive guide.",
        "twitter_title": title,
        "twitter_description": f"The ultimate {keyword} guide for 2026. Read now.",
    }


def _mock_audit() -> dict[str, Any]:
    return {
        "overall_score": 82,
        "checks": [
            {"factor": "Keyword in H1", "score": 10, "pass": True, "note": "Present in title"},
            {"factor": "Keyword in first 100 words", "score": 9, "pass": True, "note": "Found in paragraph 1"},
            {"factor": "Keyword density", "score": 7, "pass": True, "note": "1.4% - within range"},
            {"factor": "H2/H3 structure", "score": 8, "pass": True, "note": "Good heading hierarchy"},
            {"factor": "Internal link placeholders", "score": 6, "pass": True, "note": "1 placeholder found"},
            {"factor": "Image placeholders", "score": 7, "pass": True, "note": "2 placeholders found"},
            {"factor": "FAQ section", "score": 9, "pass": True, "note": "3 FAQs with schema markup"},
            {"factor": "CTA placements", "score": 8, "pass": True, "note": "2 CTAs found"},
            {"factor": "Meta title length", "score": 8, "pass": True, "note": "56 chars - good"},
            {"factor": "Meta description length", "score": 7, "pass": True, "note": "148 chars - good"},
            {"factor": "Readability", "score": 8, "pass": True, "note": "Short paragraphs, good lists"},
            {"factor": "Word count", "score": 7, "pass": True, "note": "Close to target"},
        ],
        "issues": [
            "Could add more internal link placeholders",
            "Consider adding a comparison table",
        ],
        "recommendations": [
            "Add 2-3 more internal link placeholders to related articles",
            "Include a data table comparing top tools/strategies",
            "Add alt text descriptions to image placeholders",
        ],
    }
