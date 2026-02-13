"""
02_Content_Strategy_Blog_Planning/content_planner.py

Step 3 from workflow.txt -- AI Content Strategy Generation.
Takes queued keywords and asks AI to produce a content plan with:
  - Content type, word count, title, meta description
  - Pillar/cluster classification
  - Internal linking targets
  - Publishing priority
  - Topical cluster map
"""

from __future__ import annotations

import json
from typing import Any

from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("content_planner")

# ---------------------------------------------------------------------------
# Content Strategy prompt
# ---------------------------------------------------------------------------

STRATEGY_SYSTEM_PROMPT = """\
You are a content strategist for a digital business blog.

Given a list of prioritised keywords with search volume and intent data,
determine the best content plan. For each keyword decide:

1. Content Type: blog post | ultimate guide | listicle | comparison | case study | how-to tutorial
2. Target Word Count: thin=1200, medium=2000, competitive=3000+
3. Title: SEO-optimised, click-worthy (include primary keyword)
4. Meta Description: 155 chars max, include keyword, compelling CTA
5. Pillar or Cluster: Is this a pillar page or a supporting cluster article?
6. Internal Link Targets: slugs of other planned articles it should link to
7. Publishing Priority: 1 (urgent) to 5 (can wait)

Also produce a TOPICAL CLUSTER MAP showing which pillar articles connect
to which supporting articles.

Return ONLY valid JSON:
{
  "content_plan": [
    {
      "keyword": "...",
      "content_type": "...",
      "word_count": 2000,
      "title": "...",
      "meta_description": "...",
      "pillar_or_cluster": "pillar",
      "internal_links": ["slug-1", "slug-2"],
      "priority": 1
    }
  ],
  "cluster_map": {
    "pillar_topic": ["supporting_1", "supporting_2"]
  }
}
"""


def generate_content_plan(
    niche: str,
    queued_keywords: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Send queued keywords to AI and return a content plan + cluster map.
    """
    log.info(
        "Generating content strategy for %d keywords in niche '%s'",
        len(queued_keywords), niche,
    )

    # In dry-run mode, use our own realistic mock
    if settings.dry_run:
        log.info("[DRY-RUN] Generating mock content plan")
        return _mock_content_plan(queued_keywords)

    kw_summary = json.dumps(queued_keywords, indent=2)

    user_prompt = (
        f"Niche: {niche}\n\n"
        f"Prioritised keywords to plan content for:\n{kw_summary}"
    )

    result = ask_ai_json(STRATEGY_SYSTEM_PROMPT, user_prompt)

    # Normalise response
    if isinstance(result, list):
        result = {"content_plan": result, "cluster_map": {}}

    plan = result.get("content_plan", [])
    cluster_map = result.get("cluster_map", {})

    log.info(
        "AI returned %d content plan items and %d pillar clusters",
        len(plan), len(cluster_map),
    )

    return result


# ---------------------------------------------------------------------------
# Mock response for dry-run
# ---------------------------------------------------------------------------

def _mock_content_plan(keywords: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a deterministic mock plan for dry-run testing."""
    plan_items = []
    for i, kw in enumerate(keywords):
        keyword = kw.get("Keyword", f"keyword-{i}")
        slug = keyword.lower().replace(" ", "-")
        plan_items.append({
            "keyword": keyword,
            "content_type": "ultimate guide" if i == 0 else "blog post",
            "word_count": 3000 if i == 0 else 2000,
            "title": f"The Complete Guide to {keyword.title()}" if i == 0
                     else f"How to Master {keyword.title()} in 2026",
            "meta_description": f"Learn everything about {keyword} with our "
                                f"actionable guide. Get started today.",
            "pillar_or_cluster": "pillar" if i == 0 else "cluster",
            "internal_links": [keywords[0].get("Keyword", "main").lower()
                               .replace(" ", "-")] if i > 0 else [],
            "priority": min(i + 1, 5),
        })

    # Build cluster map: first keyword is pillar, rest are supporting
    pillar = keywords[0].get("Keyword", "main") if keywords else "main"
    supporters = [kw.get("Keyword", "") for kw in keywords[1:]]
    cluster_map = {pillar: supporters} if supporters else {}

    return {"content_plan": plan_items, "cluster_map": cluster_map}
