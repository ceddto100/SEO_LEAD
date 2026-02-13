"""
11_Performance_Feedback_Loop/optimizer.py

Steps 2-6 -- AI analyzes performance and generates optimization actions.
"""
from __future__ import annotations
from typing import Any
from shared.config import settings
from shared.ai_client import ask_ai_json
from shared.logger import get_logger

log = get_logger("optimizer")

ANALYSIS_SYSTEM_PROMPT = """\
You are a content performance optimizer. Analyze performance data and create
an optimization action plan.

Analyze:
1. TOP PERFORMERS - Why are they working? Patterns to replicate.
2. UNDERPERFORMERS - Issues and specific fixes.
3. ALMOST-THERE - Pages at positions 8-20 that could reach page 1.
4. CONTENT REFRESH - Declining pages (>20% drop).
5. KEYWORD ADJUSTMENTS - New targets, deprioritize, long-tail opportunities.

Return ONLY valid JSON:
{
  "top_performer_insights": {
    "patterns": ["..."],
    "replicate_actions": ["..."]
  },
  "underperformer_fixes": [
    {"url": "...", "issues": ["..."], "actions": ["..."], "priority": "high"}
  ],
  "almost_there": [
    {"url": "...", "keyword": "...", "current_position": 0, "actions": ["..."]}
  ],
  "refresh_candidates": [
    {"url": "...", "decline": "...", "actions": ["..."]}
  ],
  "keyword_adjustments": {
    "new_targets": ["..."], "deprioritize": ["..."], "long_tail": ["..."]
  }
}
"""

def analyze_performance(perf_data: dict[str, Any]) -> dict[str, Any]:
    log.info("Running AI performance analysis...")
    if settings.dry_run:
        log.info("[DRY-RUN] Returning mock optimization analysis")
        return {
            "top_performer_insights": {
                "patterns": ["Listicles perform 2x better", "Transactional intent converts higher"],
                "replicate_actions": ["Create 3 more comparison posts", "Add more case studies"],
            },
            "underperformer_fixes": [{
                "url": "/blog/seo-tips", "issues": ["Thin content (800w)", "No internal links"],
                "actions": ["Expand to 2500 words", "Add 5 internal links", "Add FAQ schema"],
                "priority": "high",
            }],
            "almost_there": [{
                "url": "/blog/crm-guide", "keyword": "crm comparison",
                "current_position": 11,
                "actions": ["Add comparison table", "Update title tag"],
            }],
            "refresh_candidates": [{
                "url": "/blog/email-tools", "decline": "-50%",
                "actions": ["Update tool list for 2026", "Add pricing section"],
            }],
            "keyword_adjustments": {
                "new_targets": ["ai crm tools", "marketing automation comparison"],
                "deprioritize": ["generic seo tips"],
                "long_tail": ["best crm for small business 2026"],
            },
        }
    return ask_ai_json(ANALYSIS_SYSTEM_PROMPT, f"Performance Data:\n{perf_data}")

def build_refresh_brief(page: dict[str, Any]) -> str:
    """Build a content refresh brief for Workflow 03."""
    return (f"CONTENT REFRESH BRIEF\n"
            f"URL: {page.get('url', '')}\n"
            f"Decline: {page.get('decline', 'unknown')}\n"
            f"Issues: {', '.join(page.get('issues', page.get('actions', [])))}\n"
            f"Actions Required:\n" +
            "\n".join(f"  - {a}" for a in page.get("actions", [])))
