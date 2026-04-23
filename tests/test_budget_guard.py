"""Tests for utils/budget_guard.py — dashboard budget enforcement."""
import pytest
from unittest.mock import MagicMock, patch

from utils.budget_guard import DashboardBudgetExceeded, ensure_dashboard_budget_available


class _FakeBudgetSummary:
    def __init__(self, exceeded: bool):
        self.budget = MagicMock()
        self.budget.exceeded_any = exceeded


def _mock_settings(over_budget_continue=False, daily=None, monthly=None, yearly=None):
    return {
        "over_budget_continue": over_budget_continue,
        "daily_budget_usd": daily,
        "monthly_budget_usd": monthly,
        "yearly_budget_usd": yearly,
    }


class TestEnsureDashboardBudgetAvailable:
    def test_raises_when_budget_exceeded(self):
        with patch("utils.budget_guard.get_cli_settings", return_value=_mock_settings()):
            with patch("utils.budget_guard.tracker") as mock_tracker:
                mock_tracker.get_dashboard_summary.return_value = _FakeBudgetSummary(exceeded=True)
                with pytest.raises(DashboardBudgetExceeded):
                    ensure_dashboard_budget_available()

    def test_passes_when_budget_not_exceeded(self):
        with patch("utils.budget_guard.get_cli_settings", return_value=_mock_settings()):
            with patch("utils.budget_guard.tracker") as mock_tracker:
                mock_tracker.get_dashboard_summary.return_value = _FakeBudgetSummary(exceeded=False)
                ensure_dashboard_budget_available()  # must not raise

    def test_over_budget_continue_skips_check(self):
        """When over_budget_continue=True, tracker is never called."""
        with patch("utils.budget_guard.get_cli_settings", return_value=_mock_settings(over_budget_continue=True)):
            with patch("utils.budget_guard.tracker") as mock_tracker:
                ensure_dashboard_budget_available()
                mock_tracker.get_dashboard_summary.assert_not_called()

    def test_error_message_mentions_budget(self):
        with patch("utils.budget_guard.get_cli_settings", return_value=_mock_settings()):
            with patch("utils.budget_guard.tracker") as mock_tracker:
                mock_tracker.get_dashboard_summary.return_value = _FakeBudgetSummary(exceeded=True)
                with pytest.raises(DashboardBudgetExceeded, match="budget"):
                    ensure_dashboard_budget_available()

    def test_dashboard_budget_exceeded_is_exception(self):
        exc = DashboardBudgetExceeded(message="Budget exceeded")
        assert isinstance(exc, Exception)
        assert str(exc) == "Budget exceeded"
