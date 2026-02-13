"""
shared/google_sheets.py — Google Sheets client for the SEO_LEAD platform.

Uses gspread + service-account auth.  Every workflow that reads/writes sheets
creates a SheetsClient instance:

    from shared.google_sheets import SheetsClient
    sheets = SheetsClient()
    rows = sheets.read_rows("NicheInputs")
    sheets.append_rows("KeywordResearch", [{"Keyword": "...", "Volume": 1200}])
"""

from __future__ import annotations

import time
from typing import Any

from shared.config import settings
from shared.logger import get_logger

log = get_logger("google_sheets")

# Rate limiter: minimum seconds between Sheets API calls
_MIN_API_INTERVAL = 0.5  # 120 calls/min max (well under the 300/min quota)
_last_api_call = 0.0


def _rate_limit():
    """Enforce minimum interval between Sheets API calls."""
    global _last_api_call
    now = time.time()
    elapsed = now - _last_api_call
    if elapsed < _MIN_API_INTERVAL:
        time.sleep(_MIN_API_INTERVAL - elapsed)
    _last_api_call = time.time()

# ── Lazy imports so dry-run mode works without google-auth installed ─────────
_gc = None  # gspread.Client singleton


def _get_gc():
    global _gc
    if _gc is None:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        sa_path = settings.google_sa_path()
        log.info("Authenticating with service account: %s", sa_path)
        creds = Credentials.from_service_account_file(str(sa_path), scopes=scopes)
        _gc = gspread.authorize(creds)
    return _gc


class SheetsClient:
    """
    Thin wrapper around a single Google Spreadsheet.

    The spreadsheet ID comes from .env GOOGLE_SHEET_ID.
    Each tab (worksheet) is addressed by name.
    """

    def __init__(self, sheet_id: str | None = None):
        self._sheet_id = sheet_id or settings.google_sheet_id
        self._spreadsheet = None

    # ── Internal ─────────────────────────────────────────────────────────

    def _get_spreadsheet(self):
        if self._spreadsheet is None:
            if settings.dry_run:
                log.info("[DRY-RUN] Skipping Google Sheets connection")
                return None
            gc = _get_gc()
            self._spreadsheet = gc.open_by_key(self._sheet_id)
            log.info("Opened spreadsheet: %s", self._spreadsheet.title)
        return self._spreadsheet

    def _get_worksheet(self, tab_name: str):
        """Get or create a worksheet by name."""
        ss = self._get_spreadsheet()
        if ss is None:
            return None
        try:
            return ss.worksheet(tab_name)
        except Exception:
            log.info("Tab '%s' not found — creating it", tab_name)
            return ss.add_worksheet(title=tab_name, rows=1000, cols=20)

    # ── Public API ───────────────────────────────────────────────────────

    def read_rows(
        self,
        tab_name: str,
        filters: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Read all rows from a tab as a list of dicts (header row = keys).

        Optional filters: {"Status": "new"} → only rows where Status == "new".
        """
        if settings.dry_run:
            log.info("[DRY-RUN] Mock read from '%s'", tab_name)
            return self._mock_read(tab_name)

        ws = self._get_worksheet(tab_name)
        if ws is None:
            return []

        _rate_limit()
        records = ws.get_all_records()
        log.info("Read %d rows from '%s'", len(records), tab_name)

        if filters:
            records = [
                r for r in records
                if all(str(r.get(k, "")) == str(v) for k, v in filters.items())
            ]
            log.info("After filters: %d rows", len(records))

        return records

    def append_rows(
        self,
        tab_name: str,
        rows: list[dict[str, Any]],
        *,
        headers: list[str] | None = None,
    ) -> int:
        """
        Append rows to a tab.  If the tab is empty, writes a header row first.

        Returns the number of rows written.
        """
        if not rows:
            return 0

        if settings.dry_run:
            log.info("[DRY-RUN] Would write %d rows to '%s'", len(rows), tab_name)
            for i, row in enumerate(rows[:3]):  # show first 3 in logs
                log.debug("  Row %d: %s", i + 1, row)
            return len(rows)

        ws = self._get_worksheet(tab_name)
        if ws is None:
            return 0

        # Determine header order
        if headers is None:
            headers = list(rows[0].keys())

        # If sheet is empty, write headers first
        existing = ws.get_all_values()
        if not existing:
            ws.append_row(headers)
            log.info("Wrote header row to '%s': %s", tab_name, headers)

        # Write data rows
        _rate_limit()
        data = [[row.get(h, "") for h in headers] for row in rows]
        ws.append_rows(data)
        log.info("Appended %d rows to '%s'", len(data), tab_name)
        return len(data)

    def update_cell(
        self,
        tab_name: str,
        row: int,
        col: int,
        value: Any,
    ) -> None:
        """Update a single cell (1-indexed row and col)."""
        if settings.dry_run:
            log.info("[DRY-RUN] Would update '%s' cell (%d,%d) = %s", tab_name, row, col, value)
            return

        ws = self._get_worksheet(tab_name)
        if ws:
            ws.update_cell(row, col, value)
            log.debug("Updated '%s' (%d,%d) → %s", tab_name, row, col, value)

    # ── Mocks for dry-run ────────────────────────────────────────────────

    @staticmethod
    def _mock_read(tab_name: str) -> list[dict[str, Any]]:
        """Return sample data for dry-run mode."""
        if tab_name == "NicheInputs":
            return [
                {"Niche": "lead generation", "SeedKeywords": "crm software,email marketing,lead gen tools"},
            ]
        return []

    def has_row(
        self,
        tab_name: str,
        key_column: str,
        key_value: str,
    ) -> bool:
        """
        Check if a row with the given key value already exists.
        Used for deduplication before appending.
        """
        if settings.dry_run:
            log.info("[DRY-RUN] Dedup check '%s' in '%s' -> False (mock)", key_value, tab_name)
            return False
        rows = self.read_rows(tab_name)
        return any(
            str(r.get(key_column, "")).strip().lower() == key_value.strip().lower()
            for r in rows
        )
