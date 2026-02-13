"""
shared/logger.py — Structured logging for the SEO_LEAD platform.

Usage:
    from shared.logger import get_logger
    log = get_logger("workflow_01")
    log.info("Starting keyword research…")
"""

import logging
import sys
from pathlib import Path


_CONFIGURED = False


def _configure_root() -> None:
    """One-time root logger setup with console + file output."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    _CONFIGURED = True

    from shared.config import settings  # deferred to avoid circular import

    level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Ensure logs/ directory exists
    log_dir = settings.project_root / "logs"
    log_dir.mkdir(exist_ok=True)

    fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(name)-20s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    console.setLevel(level)

    # File handler (rotating daily is overkill for now; simple append)
    file_handler = logging.FileHandler(log_dir / "seo_lead.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    file_handler.setLevel(level)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(console)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Configures root logger on first call."""
    _configure_root()
    return logging.getLogger(name)
