"""
SEO_LEAD Shared Module — Reusable utilities for all 12 workflows.
"""

from shared.config import settings
from shared.ai_client import ask_ai, ask_ai_json
from shared.google_sheets import SheetsClient
from shared.notifier import send_notification
from shared.logger import get_logger

__all__ = [
    "settings",
    "ask_ai",
    "ask_ai_json",
    "SheetsClient",
    "send_notification",
    "get_logger",
]
