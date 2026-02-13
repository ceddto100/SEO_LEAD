"""
01_Keyword_Market_Research/ai_clustering.py

Step 4 from workflow.txt — Sends keyword data to AI for:
  1. Generating 30 additional long-tail variations
  2. Clustering ALL keywords by search intent
  3. Scoring each keyword on opportunity (1-10)
"""

from __future__ import annotations

from typing import Any

from shared.ai_client import ask_ai_json
from shared.config import settings
from shared.logger import get_logger

log = get_logger("ai_clustering")


# ── Prompt Template ──────────────────────────────────────────────────────────

CLUSTERING_SYSTEM_PROMPT = """\
You are an expert SEO keyword strategist. You analyze keyword data and \
produce structured, actionable keyword clustering reports. Always return \
valid JSON — no commentary outside the JSON object.\
"""

CLUSTERING_USER_PROMPT = """\
Given this niche and seed keyword data:

**Niche:** {niche}

**Keyword Data:**
{keyword_data_json}

**Tasks:**
1. Generate 30 additional long-tail keyword variations relevant to the niche.
2. Cluster ALL keywords (original + new) into groups by search intent:
   - **informational** (how-to, what-is, guide, tutorial)
   - **transactional** (buy, best, pricing, review, comparison)
   - **navigational** (brand + keyword, specific tool/product names)
3. Score each keyword 1–10 on "opportunity":
   - High volume + low competition = high score (8–10)
   - Medium volume + medium competition = medium score (5–7)
   - Low volume or high competition = low score (1–4)
4. Include original metrics (search_volume, competition, cpc) when available.
   For AI-generated keywords, estimate reasonable values.

**Return exactly this JSON structure:**
{{
  "clusters": [
    {{
      "intent": "informational",
      "keywords": [
        {{
          "keyword": "how to generate leads online",
          "search_volume": 3200,
          "competition": "low",
          "cpc": 3.50,
          "opportunity_score": 8,
          "source": "original"
        }}
      ]
    }},
    {{
      "intent": "transactional",
      "keywords": [...]
    }},
    {{
      "intent": "navigational",
      "keywords": [...]
    }}
  ],
  "total_keywords": 45,
  "top_opportunities": [
    {{
      "keyword": "...",
      "opportunity_score": 10,
      "intent": "transactional"
    }}
  ]
}}
"""


# ── Public API ───────────────────────────────────────────────────────────────

def cluster_keywords(
    niche: str,
    keyword_data: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Send keyword data to AI for expansion, clustering, and scoring.

    Returns the full clustering result dict with:
        clusters, total_keywords, top_opportunities
    """
    log.info("Clustering %d keywords for niche '%s'…", len(keyword_data), niche)

    # Format keyword data for the prompt
    import json
    kw_json = json.dumps(keyword_data, indent=2)

    user_prompt = CLUSTERING_USER_PROMPT.format(
        niche=niche,
        keyword_data_json=kw_json,
    )

    result = ask_ai_json(CLUSTERING_SYSTEM_PROMPT, user_prompt, temperature=0.6)

    # Validate structure
    if isinstance(result, dict) and "clusters" in result:
        total = sum(len(c.get("keywords", [])) for c in result["clusters"])
        log.info("AI returned %d clusters with %d total keywords", len(result["clusters"]), total)
    else:
        log.warning("AI response missing expected 'clusters' key")

    return result


def flatten_clusters(clustering_result: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Flatten clustered keywords into a flat list with intent added to each row.

    Useful for writing to Google Sheets.
    """
    rows = []
    for cluster in clustering_result.get("clusters", []):
        intent = cluster.get("intent", "unknown")
        for kw in cluster.get("keywords", []):
            rows.append({
                "Keyword": kw.get("keyword", ""),
                "Volume": kw.get("search_volume", 0),
                "Competition": kw.get("competition", ""),
                "CPC": kw.get("cpc", 0),
                "Intent": intent,
                "Opportunity Score": kw.get("opportunity_score", 0),
                "Source": kw.get("source", "ai_generated"),
            })

    # Sort by opportunity score descending
    rows.sort(key=lambda r: r.get("Opportunity Score", 0), reverse=True)
    log.info("Flattened %d keyword rows", len(rows))
    return rows
