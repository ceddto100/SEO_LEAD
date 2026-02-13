"""
03_AI_Blog_Writing_SEO/sheets_writer.py

Steps 8-10 from workflow.txt -- Save results to Google Sheets:
  - Update ContentCalendar status to "written"
  - Queue article for publishing in "PublishQueue" tab
"""

from __future__ import annotations

import json
from typing import Any

from shared.config import settings
from shared.google_sheets import SheetsClient
from shared.logger import get_logger

log = get_logger("wf03_sheets")

# ── Column definitions ───────────────────────────────────────────────────────

PUBLISH_QUEUE_HEADERS = [
    "Title", "Slug", "Keyword", "Meta Title", "Meta Description",
    "Schema JSON", "Publish Date", "Image Needed", "SEO Score",
    "Word Count", "Status",
]


def update_calendar_status(
    keyword: str,
    seo_score: int,
) -> int:
    """
    Update the ContentCalendar row for this keyword:
      - Status = "written"
      - SEO_Score = score
    """
    if settings.dry_run:
        log.info(
            "[DRY-RUN] Would update ContentCalendar: keyword='%s', "
            "status='written', seo_score=%d",
            keyword, seo_score,
        )
        return 1

    sheets = SheetsClient()
    rows = sheets.read_rows("ContentCalendar")
    updated = 0

    for i, row in enumerate(rows):
        if row.get("Keyword", "").lower() == keyword.lower() and \
           row.get("Status", "").lower() == "planned":
            row_index = i + 2  # 1-indexed + header row
            sheets.update_cell("ContentCalendar", row_index, "Status", "written")
            sheets.update_cell("ContentCalendar", row_index, "SEO Score", str(seo_score))
            updated += 1
            break

    log.info("Updated %d ContentCalendar rows to 'written'", updated)
    return updated


def queue_for_publishing(
    title: str,
    meta_data: dict[str, Any],
    publish_date: str,
    seo_score: int,
    word_count: int,
) -> int:
    """
    Add the article to the PublishQueue tab for Workflow 05 to pick up.
    """
    slug = meta_data.get("slug", "untitled")
    schema_json = json.dumps(meta_data.get("schema_markup", {}))

    row = {
        "Title": title,
        "Slug": slug,
        "Keyword": meta_data.get("focus_keyword", ""),
        "Meta Title": meta_data.get("meta_title", title),
        "Meta Description": meta_data.get("meta_description", ""),
        "Schema JSON": schema_json,
        "Publish Date": publish_date,
        "Image Needed": "yes",
        "SEO Score": seo_score,
        "Word Count": word_count,
        "Status": "ready",
    }

    sheets = SheetsClient()
    count = sheets.append_rows("PublishQueue", [row], headers=PUBLISH_QUEUE_HEADERS)
    log.info("Queued '%s' for publishing (slug: %s, score: %d)", title, slug, seo_score)
    return count


def save_all_results(
    title: str,
    keyword: str,
    meta_data: dict[str, Any],
    publish_date: str,
    seo_score: int,
    word_count: int,
) -> dict[str, int]:
    """
    Write all Workflow 03 results to Google Sheets.

    Returns a dict of {action: count}.
    """
    summary: dict[str, int] = {}

    summary["CalendarUpdated"] = update_calendar_status(keyword, seo_score)
    summary["PublishQueued"] = queue_for_publishing(
        title, meta_data, publish_date, seo_score, word_count
    )

    return summary
