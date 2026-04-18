from __future__ import annotations

from datetime import datetime, timedelta

from core.dashboard import history as history_mod
from core.dashboard import total as total_mod
from core.dashboard.state import DashboardRangeState


def test_history_default_one_day(monkeypatch):
    state = DashboardRangeState(label="test")
    monkeypatch.setattr(history_mod, "clear_screen", lambda: None)
    monkeypatch.setattr(history_mod, "header", lambda *args, **kwargs: None)
    monkeypatch.setattr(history_mod, "export_pdf", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        history_mod.dashboard_data,
        "summarize_tokens_by_cli_batches",
        lambda s, u: [
            {
                "batch_idx": 1,
                "timestamp": "2026-04-16T12:00:00",
                "mode": "ask",
                "by_role": {"A": {"requests": 1}},
                "cost_usd": 0.01,
                "totals": {"total_tokens": 5},
            }
        ],
    )
    responses = iter(["back"])
    monkeypatch.setattr(history_mod.Prompt, "ask", lambda *args, **kwargs: next(responses))
    history_mod.show_history_browser(state)
    assert state.since is not None
    assert state.until is not None


def test_check_turn_renders_detail(monkeypatch):
    state = DashboardRangeState(label="test")
    anchor = datetime(2026, 4, 16, 12, 0, 0)
    state.since = anchor
    state.until = anchor + timedelta(days=1)
    batch = {
        "batch_idx": 1,
        "timestamp": "2026-04-16T12:00:00",
        "mode": "ask",
        "cost_usd": 0.02,
        "totals": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        "by_model": {"m1": {"requests": 1, "prompt_tokens": 10, "completion_tokens": 5, "cost_usd": 0.02}},
        "by_role": {"A": {"requests": 1, "prompt_tokens": 10, "completion_tokens": 5, "cost_usd": 0.02}},
    }
    monkeypatch.setattr(history_mod, "clear_screen", lambda: None)
    monkeypatch.setattr(history_mod, "header", lambda *args, **kwargs: None)
    monkeypatch.setattr(history_mod, "export_pdf", lambda *args, **kwargs: None)
    monkeypatch.setattr(history_mod, "_dashboard_panel", lambda *args, **kwargs: None)
    monkeypatch.setattr(history_mod.dashboard_data, "summarize_tokens_by_cli_batches", lambda s, u: [batch])
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: "")
    responses = iter(["check", "1", "back"])
    monkeypatch.setattr(history_mod.Prompt, "ask", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(history_mod, "_show_batch_detail", lambda *args, **kwargs: None)
    history_mod.show_history_browser(state)


def test_total_table_uses_table(monkeypatch):
    state = DashboardRangeState(label="test")
    monkeypatch.setattr(total_mod, "clear_screen", lambda: None)
    monkeypatch.setattr(total_mod, "header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        total_mod.dashboard_data,
        "read_usage_log",
        lambda last_n=8000: [{"role_key": "A", "agent": "A", "model": "m1", "total_tokens": 10, "cost_usd": 0.1}],
    )
    monkeypatch.setattr(
        total_mod.dashboard_data,
        "aggregate_rows_by_role_model",
        lambda rows: [{"role": "A", "model": "m1", "requests": 1, "tokens": 10, "cost": 0.1}],
    )
    monkeypatch.setattr(total_mod, "ask_choice", lambda *args, **kwargs: "back")
    total_mod.show_total_browser(state)
