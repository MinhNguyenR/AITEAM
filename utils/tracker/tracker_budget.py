"""Budget metrics and evaluation (wallet-agnostic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


def _sf(v: Any) -> float:
    try:
        return float(v or 0.0)
    except (TypeError, ValueError, OverflowError):
        return 0.0


@dataclass
class BudgetMetric:
    spent_usd: float
    limit_usd: Optional[float]
    status: str
    percent: Optional[float]
    unlimited: bool


@dataclass
class BudgetEvaluation:
    daily: BudgetMetric
    monthly: BudgetMetric
    yearly: BudgetMetric
    exceeded_any: bool


@dataclass
class DashboardSummary:
    total_credits: float
    remaining_credits: float
    currency: str
    requests_today: int
    tokens_today: int
    spend_today: float
    period_usage: Dict[str, Dict[str, float]]
    budget: BudgetEvaluation


def _metric(spent: float, limit: Optional[float]) -> BudgetMetric:
    spent = _sf(spent)
    if limit is None:
        return BudgetMetric(spent_usd=spent, limit_usd=None, status="UNLIMITED", percent=None, unlimited=True)
    if limit <= 0:
        return BudgetMetric(spent_usd=spent, limit_usd=0.0, status="EXCEEDED", percent=1.0, unlimited=False)
    pct = spent / limit
    if pct < 0.8:
        status = "OK"
    elif pct <= 1.0:
        status = "WARNING"
    else:
        status = "EXCEEDED"
    return BudgetMetric(spent_usd=spent, limit_usd=limit, status=status, percent=pct, unlimited=False)


def evaluate_budget(
    period_usage: Dict[str, Dict[str, float]],
    daily_budget_usd: Optional[float],
    monthly_budget_usd: Optional[float],
    yearly_budget_usd: Optional[float],
) -> BudgetEvaluation:
    daily = _metric(period_usage["daily"]["spend"], daily_budget_usd)
    monthly = _metric(period_usage["monthly"]["spend"], monthly_budget_usd)
    yearly = _metric(period_usage["yearly"]["spend"], yearly_budget_usd)
    exceeded_any = any(x.status == "EXCEEDED" for x in (daily, monthly, yearly))
    return BudgetEvaluation(daily=daily, monthly=monthly, yearly=yearly, exceeded_any=exceeded_any)


def should_block_all_requests(summary: DashboardSummary) -> bool:
    return summary.remaining_credits <= 0
