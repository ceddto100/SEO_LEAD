"""
02_Content_Strategy_Blog_Planning/sheets_writer.py

Steps 6-8 from workflow.txt -- Save results to Google Sheets:
  - Content calendar    -> "ContentCalendar" tab
  - Blog outlines       -> "BlogOutlines" tab (formatted text)
  - Cluster map         -> "ClusterMap" tab
  - Update ContentQueue -> set Status = "planned"
"""

from __future__ import annotations

from typing import Any

from shared.config import settings
from shared.google_sheets import SheetsClient
from shared.logger import get_logger

log = get_logger("wf02_sheets")

# ── Column definitions ───────────────────────────────────────────────────────

CALENDAR_HEADERS = [
    "Title", "Keyword", "Type", "Word Count", "Publish Date",
    "Status", "Priority", "Pillar/Cluster", "Slug",
    "Meta Description", "Internal Links",
]

OUTLINE_HEADERS = [
    "Title", "Slug", "Keyword", "Sections", "FAQs", "Outline Text",
]

CLUSTER_MAP_HEADERS = [
    "Pillar Topic", "Supporting Articles",
]


def save_calendar(
    calendar: list[dict[str, Any]],
) -> int:
    """Write the content calendar to the ContentCalendar tab."""
    sheets = SheetsClient()
    count = sheets.append_rows("ContentCalendar", calendar, headers=CALENDAR_HEADERS)
    log.info("Saved %d rows to ContentCalendar", count)
    return count


def save_outlines(
    outlines: list[dict[str, Any]],
    content_plan: list[dict[str, Any]],
) -> int:
    """
    Write outline summaries to the BlogOutlines tab.

    Each row has: Title, Slug, Keyword, section count, FAQ count, and
    the full outline as formatted text.
    """
    from .outline_generator import format_outline_text

    rows = []
    for outline, plan_item in zip(outlines, content_plan):
        rows.append({
            "Title": outline.get("title", ""),
            "Slug": outline.get("slug", ""),
            "Keyword": plan_item.get("keyword", ""),
            "Sections": len(outline.get("outline", [])),
            "FAQs": len(outline.get("faq", [])),
            "Outline Text": format_outline_text(outline),
        })

    sheets = SheetsClient()
    count = sheets.append_rows("BlogOutlines", rows, headers=OUTLINE_HEADERS)
    log.info("Saved %d outlines to BlogOutlines", count)
    return count


def save_cluster_map(cluster_map: dict[str, list[str]]) -> int:
    """Write the topical cluster map to the ClusterMap tab."""
    rows = []
    for pillar, supporters in cluster_map.items():
        rows.append({
            "Pillar Topic": pillar,
            "Supporting Articles": ", ".join(supporters),
        })

    if not rows:
        log.info("No cluster map data to save")
        return 0

    sheets = SheetsClient()
    count = sheets.append_rows("ClusterMap", rows, headers=CLUSTER_MAP_HEADERS)
    log.info("Saved %d cluster map entries", count)
    return count


def update_queue_status(
    processed_keywords: list[str],
) -> int:
    """
    Update the ContentQueue tab: set Status = 'planned' for processed keywords.

    In dry-run mode, just logs what would be updated.
    """
    if not processed_keywords:
        return 0

    if settings.dry_run:
        log.info(
            "[DRY-RUN] Would update %d ContentQueue rows to status='planned'",
            len(processed_keywords),
        )
        return len(processed_keywords)

    sheets = SheetsClient()
    updated = 0

    # Read current queue to find row indices
    queue_rows = sheets.read_rows("ContentQueue")
    for i, row in enumerate(queue_rows):
        kw = row.get("Keyword", "")
        if kw in processed_keywords and row.get("Status", "") == "new":
            # gspread rows are 1-indexed, +1 for header row
            row_index = i + 2
            sheets.update_cell("ContentQueue", row_index, "Status", "planned")
            updated += 1

    log.info("Updated %d ContentQueue rows to status='planned'", updated)
    return updated


def save_all_results(
    calendar: list[dict[str, Any]],
    outlines: list[dict[str, Any]],
    content_plan: list[dict[str, Any]],
    cluster_map: dict[str, list[str]],
    processed_keywords: list[str],
) -> dict[str, int]:
    """
    Write all Workflow 02 results to Google Sheets.

    Returns a dict of {tab_name: rows_written}.
    """
    summary: dict[str, int] = {}

    summary["ContentCalendar"] = save_calendar(calendar)
    summary["BlogOutlines"] = save_outlines(outlines, content_plan)
    summary["ClusterMap"] = save_cluster_map(cluster_map)
    summary["QueueUpdated"] = update_queue_status(processed_keywords)

    return summary
