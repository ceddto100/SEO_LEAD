"""
shared/config.py — Central configuration loader for the SEO_LEAD platform.

Reads all settings from the project-root .env file and exposes them as a
typed Settings dataclass.  Every module does:

    from shared.config import settings
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# ── Locate .env relative to project root ─────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_env_path = PROJECT_ROOT / ".env"

if _env_path.exists():
    load_dotenv(_env_path)
else:
    # Fall back to .env.example so the code can still import (dry-run mode)
    _example = PROJECT_ROOT / ".env.example"
    if _example.exists():
        load_dotenv(_example)


def _env(key: str, default: str = "") -> str:
    """Read an env var, stripping whitespace."""
    return os.getenv(key, default).strip()


def _env_int(key: str, default: int = 0) -> int:
    val = _env(key, str(default))
    try:
        return int(val)
    except ValueError:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    return _env(key, str(default)).lower() in ("true", "1", "yes")


# ── Settings dataclass ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Settings:
    """Immutable platform-wide settings loaded from .env."""

    # AI Provider
    openai_api_key: str = field(default_factory=lambda: _env("OPENAI_API_KEY"))
    openai_model: str = field(default_factory=lambda: _env("OPENAI_MODEL", "gpt-4o"))
    openai_max_tokens: int = field(default_factory=lambda: _env_int("OPENAI_MAX_TOKENS", 4096))

    # SEO Data Provider (DataForSEO)
    dataforseo_login: str = field(default_factory=lambda: _env("DATAFORSEO_LOGIN"))
    dataforseo_password: str = field(default_factory=lambda: _env("DATAFORSEO_PASSWORD"))
    seo_location_code: int = field(default_factory=lambda: _env_int("SEO_LOCATION_CODE", 2840))
    seo_language_code: str = field(default_factory=lambda: _env("SEO_LANGUAGE_CODE", "en"))

    # Google Sheets
    google_service_account_json: str = field(
        default_factory=lambda: _env("GOOGLE_SERVICE_ACCOUNT_JSON", "credentials/service_account.json")
    )
    google_sheet_id: str = field(default_factory=lambda: _env("GOOGLE_SHEET_ID"))

    # Notifications
    notification_method: str = field(default_factory=lambda: _env("NOTIFICATION_METHOD", "none"))
    smtp_host: str = field(default_factory=lambda: _env("SMTP_HOST", "smtp.gmail.com"))
    smtp_port: int = field(default_factory=lambda: _env_int("SMTP_PORT", 587))
    smtp_user: str = field(default_factory=lambda: _env("SMTP_USER"))
    smtp_password: str = field(default_factory=lambda: _env("SMTP_PASSWORD"))
    notification_to: str = field(default_factory=lambda: _env("NOTIFICATION_TO"))
    slack_webhook_url: str = field(default_factory=lambda: _env("SLACK_WEBHOOK_URL"))

    # Website / Niche
    niche: str = field(default_factory=lambda: _env("NICHE", "digital marketing"))
    site_url: str = field(default_factory=lambda: _env("SITE_URL", "https://yourdomain.com"))

    # WordPress Publishing (Workflow 05)
    wordpress_url: str = field(default_factory=lambda: _env("WORDPRESS_URL", "https://yourdomain.com"))
    wordpress_token: str = field(default_factory=lambda: _env("WORDPRESS_TOKEN"))

    # Workflow Settings
    min_keyword_volume: int = field(default_factory=lambda: _env_int("MIN_KEYWORD_VOLUME", 100))
    top_keywords_to_queue: int = field(default_factory=lambda: _env_int("TOP_KEYWORDS_TO_QUEUE", 10))

    # General
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    dry_run: bool = field(default_factory=lambda: _env_bool("DRY_RUN", False))

    # Computed paths
    project_root: Path = field(default_factory=lambda: PROJECT_ROOT)

    def google_sa_path(self) -> Path:
        """Resolve the service account JSON path relative to project root."""
        p = Path(self.google_service_account_json)
        if p.is_absolute():
            return p
        return self.project_root / p


# ── Singleton instance ───────────────────────────────────────────────────────
settings = Settings()
