"""
Tracking + budget source of truth for AI Team CLI.

Remote: OpenRouter credits. Local: usage JSONL. Implementation split across
tracker_* modules; this file re-exports the public API.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from utils.tracker_aggregate import (
    aggregate_rows_by_role_model,
    aggregate_usage_by_role,
    build_usage_summary,
    get_local_stats,
    get_period_usage,
    search_model_substring,
)
from utils.tracker_batches import (
    append_cli_batch,
    read_cli_batches_tail,
    summarize_tokens_by_cli_batches,
)
from utils.tracker_budget import (
    BudgetEvaluation,
    BudgetMetric,
    DashboardSummary,
    evaluate_budget,
    should_block_all_requests,
)
from utils.tracker_cache import invalidate_cache
from utils.tracker_helpers import parse_usage_timestamp, safe_float, token_io_totals
from utils.tracker_openrouter import fetch_wallet
from utils.tracker_usage import append_usage_log, compute_cost_usd, read_usage_log, read_usage_rows_timerange

__all__ = [
    "append_usage_log",
    "compute_cost_usd",
    "read_usage_log",
    "parse_usage_timestamp",
    "read_usage_rows_timerange",
    "aggregate_rows_by_role_model",
    "search_model_substring",
    "token_io_totals",
    "append_cli_batch",
    "read_cli_batches_tail",
    "summarize_tokens_by_cli_batches",
    "aggregate_usage_by_role",
    "build_usage_summary",
    "get_local_stats",
    "get_period_usage",
    "fetch_wallet",
    "BudgetMetric",
    "BudgetEvaluation",
    "DashboardSummary",
    "evaluate_budget",
    "get_dashboard_summary",
    "should_block_all_requests",
    "get_usage_summary",
    "invalidate_cache",
]


def get_dashboard_summary(
    daily_budget_usd: Optional[float],
    monthly_budget_usd: Optional[float],
    yearly_budget_usd: Optional[float],
) -> DashboardSummary:
    wallet = fetch_wallet()
    usage = get_period_usage()
    budget = evaluate_budget(usage, daily_budget_usd, monthly_budget_usd, yearly_budget_usd)
    return DashboardSummary(
        total_credits=safe_float(wallet.get("total_credits")),
        remaining_credits=safe_float(wallet.get("remaining_credits")),
        currency=str(wallet.get("currency", "USD")),
        requests_today=int(usage["daily"]["requests"]),
        tokens_today=int(usage["daily"]["tokens"]),
        spend_today=safe_float(usage["daily"]["spend"]),
        period_usage=usage,
        budget=budget,
    )


def get_usage_summary(period: str = "session") -> Dict[str, Any]:
    return build_usage_summary(period)
