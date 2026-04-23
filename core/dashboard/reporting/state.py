from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from utils.tracker import parse_usage_timestamp


@dataclass
class DashboardRangeState:
    label: str
    rows: list[dict[str, Any]] = field(default_factory=list)
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    days: int = 1
    log_page: int = 0
    batch_page: int = 0
    explorer_batch_page: int = 0

    def set_days(self, days: int) -> None:
        self.days = max(1, int(days))
        self.label = f"last {self.days} days"
        self.since = datetime.now() - timedelta(days=self.days)
        self.until = datetime.now()
        self.reset_pages()

    def set_range(self, since: datetime, until: datetime, *, label: Optional[str] = None) -> None:
        self.since = since
        self.until = until
        self.label = label or f"{since.isoformat(timespec='minutes')} … {until.isoformat(timespec='minutes')}"
        self.days = max(1, int((until - since).total_seconds() // 86400) or 1)
        self.reset_pages()

    def reset_pages(self) -> None:
        self.log_page = 0
        self.batch_page = 0
        self.explorer_batch_page = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "dashboard_history_days": self.days,
            "dashboard_history_since": self.since.isoformat() if self.since else "",
            "dashboard_history_until": self.until.isoformat() if self.until else "",
            "dashboard_history_label": self.label,
            "dashboard_history_log_page": self.log_page,
            "dashboard_history_batch_page": self.batch_page,
            "dashboard_history_explorer_batch_page": self.explorer_batch_page,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DashboardRangeState":
        days = int(payload.get("dashboard_history_days") or 1)
        since_s = str(payload.get("dashboard_history_since") or "")
        until_s = str(payload.get("dashboard_history_until") or "")
        since = parse_usage_timestamp(since_s) if since_s else None
        until = parse_usage_timestamp(until_s) if until_s else None
        label = str(payload.get("dashboard_history_label") or f"last {days} days")
        return cls(
            label=label,
            since=since,
            until=until,
            days=days,
            log_page=int(payload.get("dashboard_history_log_page") or 0),
            batch_page=int(payload.get("dashboard_history_batch_page") or 0),
            explorer_batch_page=int(payload.get("dashboard_history_explorer_batch_page") or 0),
        )


@dataclass(frozen=True)
class DashboardPalette:
    pastel_blue: str = "#6495ED"
    pastel_cyan: str = "#7FFFD4"
    pastel_lavender: str = "#C8C8FF"
    bright_blue: str = "#4169E1"


@dataclass(frozen=True)
class DashboardContext:
    settings: dict[str, Optional[float]]
    project_root: Path
    range_state: DashboardRangeState
