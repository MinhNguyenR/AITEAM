from __future__ import annotations

from datetime import datetime
from typing import Any

from utils import tracker


def read_usage_log(last_n: int = 8000) -> list[dict[str, Any]]:
    return tracker.read_usage_log(last_n=last_n)


def aggregate_rows_by_role_model(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return tracker.aggregate_rows_by_role_model(rows)


def summarize_tokens_by_cli_batches(since: datetime | None, until: datetime | None) -> list[dict[str, Any]]:
    return tracker.summarize_tokens_by_cli_batches(since, until)


__all__ = [
    "read_usage_log",
    "aggregate_rows_by_role_model",
    "summarize_tokens_by_cli_batches",
]

