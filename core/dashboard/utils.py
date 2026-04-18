from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from core.cli.ui import clear_screen
from utils import tracker


BATCH_PAGE_MAIN = 8
BATCH_PAGE_EXPLORER = 50
HISTORY_PAGE_SIZE = 50
PREVIEW_LIMIT = 72
PDF_MAX_LEN = 4000


def default_range(days: int = 1, now: datetime | None = None) -> tuple[datetime, datetime]:
    now = now or datetime.now()
    days = max(1, int(days))
    return now - timedelta(days=days), now


def safe_int(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def safe_float(v: Any) -> float:
    try:
        return float(v or 0.0)
    except (TypeError, ValueError):
        return 0.0


def format_row_time(row: dict) -> str:
    dt = tracker.parse_usage_timestamp(str(row.get("timestamp", "")))
    if dt:
        return dt.strftime("%b %d, %I:%M %p")
    return str(row.get("timestamp", ""))[:22]


def sort_rows_chronological(rows: list[dict]) -> list[dict]:
    def _key(r: dict) -> float:
        dt = tracker.parse_usage_timestamp(str(r.get("timestamp", "")))
        return dt.timestamp() if dt else 0.0

    return sorted(rows, key=_key)


def paginate(items: list[Any], page: int, page_size: int) -> tuple[list[Any], int, int]:
    total_pages = max(1, (len(items) + page_size - 1) // page_size)
    page = max(0, min(page, total_pages - 1))
    start = page * page_size
    return items[start : start + page_size], page, total_pages


def clear_dashboard_screen() -> None:
    clear_screen()
