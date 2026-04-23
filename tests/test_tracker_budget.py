"""Tests for utils/tracker/tracker_budget.py — BudgetMetric and evaluation."""
import pytest
from utils.tracker.tracker_budget import (
    BudgetEvaluation,
    BudgetMetric,
    DashboardSummary,
    _metric,
    _sf,
    evaluate_budget,
    should_block_all_requests,
)


class TestSf:
    def test_normal_float(self): assert _sf(1.5) == 1.5
    def test_none_zero(self): assert _sf(None) == 0.0
    def test_string(self): assert _sf("2.0") == 2.0
    def test_invalid_zero(self): assert _sf("bad") == 0.0


class TestMetric:
    def test_unlimited_when_no_limit(self):
        m = _metric(5.0, None)
        assert m.unlimited is True
        assert m.status == "UNLIMITED"
        assert m.percent is None

    def test_ok_when_under_80pct(self):
        m = _metric(0.5, 1.0)
        assert m.status == "OK"

    def test_warning_when_80_to_100pct(self):
        m = _metric(0.9, 1.0)
        assert m.status == "WARNING"

    def test_exceeded_when_over_limit(self):
        m = _metric(1.5, 1.0)
        assert m.status == "EXCEEDED"

    def test_zero_limit_is_exceeded(self):
        m = _metric(0.0, 0.0)
        assert m.status == "EXCEEDED"

    def test_percent_calculated(self):
        m = _metric(0.5, 2.0)
        assert m.percent == pytest.approx(0.25)


class TestEvaluateBudget:
    def _period(self, daily=0.0, monthly=0.0, yearly=0.0):
        return {
            "daily": {"spend": daily},
            "monthly": {"spend": monthly},
            "yearly": {"spend": yearly},
        }

    def test_all_ok(self):
        result = evaluate_budget(self._period(0.1, 0.5, 2.0), 10.0, 50.0, 200.0)
        assert result.exceeded_any is False
        assert result.daily.status == "OK"

    def test_daily_exceeded(self):
        result = evaluate_budget(self._period(daily=15.0), 10.0, None, None)
        assert result.exceeded_any is True
        assert result.daily.status == "EXCEEDED"

    def test_monthly_exceeded(self):
        result = evaluate_budget(self._period(monthly=100.0), None, 50.0, None)
        assert result.exceeded_any is True

    def test_all_unlimited(self):
        result = evaluate_budget(self._period(), None, None, None)
        assert result.exceeded_any is False
        assert result.daily.unlimited is True


class TestShouldBlockAllRequests:
    def _make_summary(self, remaining: float) -> DashboardSummary:
        budget = BudgetEvaluation(
            daily=BudgetMetric(0, None, "UNLIMITED", None, True),
            monthly=BudgetMetric(0, None, "UNLIMITED", None, True),
            yearly=BudgetMetric(0, None, "UNLIMITED", None, True),
            exceeded_any=False,
        )
        return DashboardSummary(
            total_credits=100.0,
            remaining_credits=remaining,
            currency="USD",
            requests_today=0,
            tokens_today=0,
            spend_today=0.0,
            period_usage={},
            budget=budget,
        )

    def test_blocks_when_no_credits(self):
        assert should_block_all_requests(self._make_summary(0.0)) is True

    def test_blocks_when_negative_credits(self):
        assert should_block_all_requests(self._make_summary(-5.0)) is True

    def test_passes_when_credits_remain(self):
        assert should_block_all_requests(self._make_summary(10.0)) is False
