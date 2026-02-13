"""
01_Keyword_Market_Research/sheets_writer.py

Steps 7-8 from workflow.txt — Saves results to Google Sheets:
  - Keyword clusters  → "KeywordResearch" tab
  - Competitor gaps    → "ContentGaps" tab
  - Top opportunities  → "ContentQueue" tab (feeds Workflow 02)
"""

from __future__ import annotations

from datetime import date
from typing import Any

from shared.config import settings
from shared.google_sheets import SheetsClient
from shared.logger import get_logger

log = get_logger("sheets_writer")


# ── Column definitions ───────────────────────────────────────────────────────

KEYWORD_HEADERS = [
    "Keyword", "Volume", "Competition", "CPC",
    "Intent", "Opportunity Score", "Source", "Date",
]

GAP_HEADERS = [
    "Keyword", "Type", "Detail", "Difficulty", "Est. Ranking Time", "Date",
]

QUEUE_HEADERS = [
    "Keyword", "Volume", "Intent", "Opportunity Score", "Status", "Date",
]


# ── Public API ───────────────────────────────────────────────────────────────

def save_all_results(
    keyword_rows: list[dict[str, Any]],
    gap_rows: list[dict[str, Any]],
    top_n: int | None = None,
) -> dict[str, int]:
    """
    Write all workflow results to Google Sheets.

    Returns a dict of {tab_name: rows_written}.
    """
    top_n = top_n or settings.top_keywords_to_queue
    today = date.today().isoformat()
    sheets = SheetsClient()

    summary = {}

    # 1. Write keyword research data
    for row in keyword_rows:
        row["Date"] = today
    summary["KeywordResearch"] = sheets.append_rows(
        "KeywordResearch", keyword_rows, headers=KEYWORD_HEADERS
    )
    log.info("Saved %d rows to KeywordResearch", summary["KeywordResearch"])

    # 2. Write competitor gap data
    for row in gap_rows:
        row["Date"] = today
    summary["ContentGaps"] = sheets.append_rows(
        "ContentGaps", gap_rows, headers=GAP_HEADERS
    )
    log.info("Saved %d rows to ContentGaps", summary["ContentGaps"])

    # 3. Push top N keywords to ContentQueue (for Workflow 02)
    queue_rows = _build_content_queue(keyword_rows, top_n, today)
    summary["ContentQueue"] = sheets.append_rows(
        "ContentQueue", queue_rows, headers=QUEUE_HEADERS
    )
    log.info("Queued %d top keywords to ContentQueue", summary["ContentQueue"])

    return summary


def _build_content_queue(
    keyword_rows: list[dict[str, Any]],
    top_n: int,
    today: str,
) -> list[dict[str, Any]]:
    """
    Select the top N opportunity keywords and format them for ContentQueue.

    Filters to keywords above the minimum volume threshold.
    """
    # Filter by minimum volume
    filtered = [
        r for r in keyword_rows
        if int(r.get("Volume", 0)) >= settings.min_keyword_volume
    ]

    # Already sorted by opportunity score from ai_clustering.flatten_clusters
    top = filtered[:top_n]

    queue = []
    for row in top:
        queue.append({
            "Keyword": row["Keyword"],
            "Volume": row["Volume"],
            "Intent": row["Intent"],
            "Opportunity Score": row["Opportunity Score"],
            "Status": "new",
            "Date": today,
        })

    return queue
