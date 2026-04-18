from __future__ import annotations

from utils import tracker


def test_aggregate_usage_by_role_and_model():
    rows = [
        {"role_key": "AMBASSADOR", "agent": "Ambassador", "model": "m1", "total_tokens": 10, "cost_usd": 0.1},
        {"role_key": "LEADER", "agent": "Leader", "model": "m1", "total_tokens": 20, "cost_usd": 0.2},
        {"role_key": "AMBASSADOR", "agent": "Ambassador", "model": "m2", "total_tokens": 5, "cost_usd": 0.05},
    ]
    agg = tracker.aggregate_rows_by_role_model(rows)
    assert agg[0]["tokens"] == 20
    by_role = tracker.aggregate_usage_by_role(rows)
    assert by_role["AMBASSADOR"]["requests"] == 2
    assert by_role["LEADER"]["tokens"] == 20


def test_evaluate_budget_flags_exceeded():
    period_usage = {
        "daily": {"spend": 12.0},
        "monthly": {"spend": 20.0},
        "yearly": {"spend": 30.0},
    }
    budget = tracker.evaluate_budget(period_usage, 10.0, None, 100.0)
    assert budget.daily.status == "EXCEEDED"
    assert budget.monthly.unlimited is True
    assert budget.yearly.status == "OK"
