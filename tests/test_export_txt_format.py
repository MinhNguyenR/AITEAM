from __future__ import annotations

from datetime import datetime, timedelta

from core.dashboard.reporting.report_model import build_usage_report
from core.dashboard.reporting.report_txt_format import format_usage_report_txt
from core.dashboard.reporting.state import DashboardRangeState


def test_usage_report_txt_has_sections():
    state = DashboardRangeState(label="unit")
    anchor = datetime(2026, 4, 16, 12, 0, 0)
    state.since = anchor
    state.until = anchor + timedelta(days=1)
    state.rows = []
    report = build_usage_report(state)
    text = format_usage_report_txt(report)
    assert "=== METADATA ===" in text
    assert "=== SUMMARY (KPI) ===" in text
    assert "=== BY ROLE ===" in text
    assert "AI TEAM — USAGE EXPORT" in text
