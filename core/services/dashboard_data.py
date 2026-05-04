"""Backward-compat shim — import from core.dashboard.application.data."""
from core.dashboard.application.data import (
    aggregate_rows_by_role_model,
    read_usage_log,
    summarize_tokens_by_cli_batches,
)

__all__ = [
    "aggregate_rows_by_role_model",
    "read_usage_log",
    "summarize_tokens_by_cli_batches",
]
