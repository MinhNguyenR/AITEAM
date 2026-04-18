from __future__ import annotations

from dataclasses import dataclass

from core.cli.state import get_cli_settings
from utils import tracker


@dataclass
class DashboardBudgetExceeded(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def ensure_dashboard_budget_available() -> None:
    settings = get_cli_settings()
    if settings.get("over_budget_continue"):
        return
    summary = tracker.get_dashboard_summary(
        daily_budget_usd=settings.get("daily_budget_usd"),
        monthly_budget_usd=settings.get("monthly_budget_usd"),
        yearly_budget_usd=settings.get("yearly_budget_usd"),
    )
    if summary.budget.exceeded_any:
        raise DashboardBudgetExceeded("Dashboard budget exceeded. Increase budget in dashboard or reset to Unlimited.")
