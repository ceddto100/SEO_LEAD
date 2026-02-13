"""
02_Content_Strategy_Blog_Planning/calendar_builder.py

Step 5 from workflow.txt -- Assign Publishing Dates.
Creates a publishing calendar from the content plan:
  - 3 posts/week (Mon, Wed, Fri) by default
  - Priority 1 articles get earliest slots
  - Pillar content spaced at least 1 week apart
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from shared.config import settings
from shared.logger import get_logger

log = get_logger("calendar_builder")

# Default publishing days: Monday=0, Wednesday=2, Friday=4
PUBLISH_WEEKDAYS = [0, 2, 4]  # Mon, Wed, Fri


def build_calendar(
    content_plan: list[dict[str, Any]],
    start_date: datetime | None = None,
    posts_per_week: int = 3,
) -> list[dict[str, Any]]:
    """
    Assign publishing dates to content plan items.

    Rules:
      - Sort by priority (1 = most urgent)
      - Assign to next available Mon/Wed/Fri slot
      - Space pillar articles at least 7 days apart
    """
    if start_date is None:
        start_date = _next_publish_day(datetime.now())

    # Sort by priority (lower = more urgent)
    sorted_plan = sorted(
        content_plan,
        key=lambda x: (x.get("priority", 5), x.get("keyword", "")),
    )

    log.info(
        "Building calendar for %d articles starting %s (%d posts/week)",
        len(sorted_plan), start_date.strftime("%Y-%m-%d"), posts_per_week,
    )

    calendar: list[dict[str, Any]] = []
    current_date = start_date
    last_pillar_date: datetime | None = None

    for item in sorted_plan:
        is_pillar = item.get("pillar_or_cluster", "cluster").lower() == "pillar"

        # If pillar, ensure at least 7 days since last pillar
        if is_pillar and last_pillar_date:
            min_pillar_date = last_pillar_date + timedelta(days=7)
            if current_date < min_pillar_date:
                current_date = _next_publish_day(min_pillar_date)

        pub_date = current_date

        if is_pillar:
            last_pillar_date = pub_date

        slug = (
            item.get("keyword", "untitled")
            .lower()
            .replace(" ", "-")
            .replace("'", "")
        )

        calendar_entry = {
            "Title": item.get("title", item.get("keyword", "Untitled")),
            "Keyword": item.get("keyword", ""),
            "Type": item.get("content_type", "blog post"),
            "Word Count": item.get("word_count", 2000),
            "Publish Date": pub_date.strftime("%Y-%m-%d"),
            "Status": "planned",
            "Priority": item.get("priority", 5),
            "Pillar/Cluster": item.get("pillar_or_cluster", "cluster"),
            "Slug": slug,
            "Meta Description": item.get("meta_description", ""),
            "Internal Links": ", ".join(item.get("internal_links", [])),
        }

        calendar.append(calendar_entry)

        # Advance to next publishing day
        current_date = _next_publish_day(pub_date + timedelta(days=1))

    log.info("Calendar built: %d articles from %s to %s",
             len(calendar),
             calendar[0]["Publish Date"] if calendar else "N/A",
             calendar[-1]["Publish Date"] if calendar else "N/A")

    return calendar


def _next_publish_day(dt: datetime) -> datetime:
    """Find the next Mon/Wed/Fri on or after the given date."""
    for offset in range(7):
        candidate = dt + timedelta(days=offset)
        if candidate.weekday() in PUBLISH_WEEKDAYS:
            return candidate
    # Fallback -- shouldn't happen
    return dt
