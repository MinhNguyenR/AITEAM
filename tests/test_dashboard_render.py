from __future__ import annotations

from core.dashboard.render import fmt_budget_line, render_session_usage_panel, render_wallet_usage
from core.dashboard.state import DashboardRangeState


class DummyMetric:
    unlimited = True
    spent_usd = 1.23
    limit_usd = None
    status = "UNLIMITED"


class DummyBudget:
    daily = DummyMetric()
    monthly = DummyMetric()
    yearly = DummyMetric()


class DummySummary:
    total_credits = 10.0
    remaining_credits = 5.0
    budget = DummyBudget()


def test_fmt_budget_line_unlimited():
    assert fmt_budget_line("DAILY", DummyMetric()) == "DAILY: $1.23 / Unlimited"


def test_render_wallet_usage_runs(monkeypatch):
    monkeypatch.setattr("core.dashboard.render.console.print", lambda *args, **kwargs: None)
    render_wallet_usage(DummySummary())


def test_render_session_usage_panel_runs(monkeypatch):
    monkeypatch.setattr("core.dashboard.render.console.print", lambda *args, **kwargs: None)
    monkeypatch.setattr("core.dashboard.render.config.list_workers", lambda: [])
    monkeypatch.setattr(
        "core.dashboard.render.tracker.get_usage_summary",
        lambda period="session": {"total_requests": 0, "total_tokens": 0, "total_cost": 0.0, "by_role": {}},
    )
    render_session_usage_panel()
