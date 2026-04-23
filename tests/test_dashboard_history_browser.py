from __future__ import annotations

from datetime import datetime, timedelta

from core.dashboard.shell import history as history_mod
from core.dashboard.reporting.state import DashboardRangeState


def test_history_browser_advances_pages(monkeypatch):
    state = DashboardRangeState(label="test")
    state.since = datetime(2026, 4, 16, 12, 0, 0)
    state.until = state.since + timedelta(days=1)
    state.rows = [{"timestamp": "2026-04-16T12:00:00"} for _ in range(3)]
    monkeypatch.setattr(history_mod, "clear_screen", lambda: None)
    monkeypatch.setattr(history_mod, "header", lambda *args, **kwargs: None)
    monkeypatch.setattr(history_mod, "_dashboard_panel", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        history_mod.dashboard_data,
        "summarize_tokens_by_cli_batches",
        lambda s, u: [{"batch_idx": 1, "timestamp": "2026-04-16T12:00:00", "mode": "ask", "totals": {}, "by_role": {}}],
    )
    responses = iter(["n", "back"])
    monkeypatch.setattr(history_mod.Prompt, "ask", lambda *args, **kwargs: next(responses))
    history_mod.show_history_browser(state)
    assert state.log_page == 1
