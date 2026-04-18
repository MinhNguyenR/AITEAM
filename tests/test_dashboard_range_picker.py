from __future__ import annotations

from datetime import datetime

from core.dashboard import render as dashboard_render


def test_pick_range_rows_custom_iso(monkeypatch):
    responses = iter(["4", "2026-04-16T10:00", "2026-04-16T12:00"])
    monkeypatch.setattr(dashboard_render, "ask_choice", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(dashboard_render.Prompt, "ask", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(dashboard_render.tracker, "read_usage_rows_timerange", lambda s, u: [{"timestamp": s.isoformat()}])
    label, rows, since, until = dashboard_render.pick_range_rows()
    assert "2026-04-16T10:00" in label
    assert rows == [{"timestamp": "2026-04-16T10:00:00"}]
    assert since == datetime(2026, 4, 16, 10, 0)
    assert until == datetime(2026, 4, 16, 12, 0)
