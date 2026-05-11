from __future__ import annotations

import sys

sys.modules.pop("core.dashboard.reporting.state", None)
from core.dashboard.shell import total as total_mod
from core.dashboard.reporting.state import DashboardRangeState


def test_batches_browser_advances_pages(monkeypatch):
    state = DashboardRangeState(label="test")
    state.since = state.until = None
    monkeypatch.setattr(total_mod, "clear_screen", lambda: None)
    monkeypatch.setattr(total_mod, "header", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        total_mod.dashboard_data,
        "summarize_tokens_by_cli_batches",
        lambda s, u: [
            {
                "batch_idx": 1,
                "timestamp": "2026-04-16T12:00:00",
                "mode": "ask",
                "prompt": "hello",
                "totals": {},
                "by_model": {},
            }
        ],
    )
    monkeypatch.setattr(total_mod.dashboard_data, "read_usage_log", lambda last_n=8000: [])
    monkeypatch.setattr(total_mod.dashboard_data, "aggregate_rows_by_role_model", lambda rows: [])
    responses = iter(["/next", "/back"])
    monkeypatch.setattr(total_mod, "ask_choice", lambda *args, **kwargs: next(responses))
    total_mod.show_total_browser(state)
    assert state.batch_page == 1
