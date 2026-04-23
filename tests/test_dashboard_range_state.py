"""Tests for core/dashboard/reporting/state.py — DashboardRangeState."""
from datetime import datetime, timedelta

from core.dashboard.reporting.state import DashboardRangeState, DashboardPalette


class TestDashboardRangeState:
    def test_defaults(self):
        s = DashboardRangeState(label="test")
        assert s.label == "test"
        assert s.days == 1
        assert s.log_page == 0
        assert s.batch_page == 0

    def test_set_days_updates_label_and_range(self):
        s = DashboardRangeState(label="")
        s.set_days(3)
        assert s.days == 3
        assert "3" in s.label
        assert s.since is not None
        assert s.until is not None
        assert (s.until - s.since).days >= 2  # approximately 3 days

    def test_set_days_clamps_to_one(self):
        s = DashboardRangeState(label="")
        s.set_days(0)
        assert s.days == 1

    def test_set_days_resets_pages(self):
        s = DashboardRangeState(label="", log_page=5, batch_page=3)
        s.set_days(1)
        assert s.log_page == 0
        assert s.batch_page == 0

    def test_set_range(self):
        since = datetime(2024, 1, 1, 0, 0, 0)
        until = datetime(2024, 1, 8, 0, 0, 0)
        s = DashboardRangeState(label="")
        s.set_range(since, until, label="week")
        assert s.since == since
        assert s.until == until
        assert s.label == "week"
        assert s.days >= 1

    def test_set_range_auto_label(self):
        since = datetime(2024, 6, 1, 12, 0, 0)
        until = datetime(2024, 6, 7, 12, 0, 0)
        s = DashboardRangeState(label="")
        s.set_range(since, until)
        assert "2024" in s.label

    def test_reset_pages(self):
        s = DashboardRangeState(label="", log_page=10, batch_page=5, explorer_batch_page=3)
        s.reset_pages()
        assert s.log_page == 0
        assert s.batch_page == 0
        assert s.explorer_batch_page == 0

    def test_to_dict(self):
        s = DashboardRangeState(label="test", days=2, log_page=1, batch_page=2)
        d = s.to_dict()
        assert d["dashboard_history_days"] == 2
        assert d["dashboard_history_label"] == "test"
        assert d["dashboard_history_log_page"] == 1

    def test_from_dict_roundtrip(self):
        original = DashboardRangeState(label="test", days=5, log_page=2)
        d = original.to_dict()
        restored = DashboardRangeState.from_dict(d)
        assert restored.label == "test"
        assert restored.days == 5
        assert restored.log_page == 2

    def test_from_dict_empty(self):
        s = DashboardRangeState.from_dict({})
        assert s.days == 1
        assert s.log_page == 0

    def test_from_dict_with_since_until(self):
        d = {
            "dashboard_history_days": 3,
            "dashboard_history_since": "2024-06-01T00:00:00",
            "dashboard_history_until": "2024-06-04T00:00:00",
            "dashboard_history_label": "custom",
        }
        s = DashboardRangeState.from_dict(d)
        assert s.label == "custom"
        assert s.since is not None
        assert s.until is not None


class TestDashboardPalette:
    def test_default_colors(self):
        p = DashboardPalette()
        assert "#" in p.pastel_blue
        assert "#" in p.pastel_cyan

    def test_is_frozen(self):
        import pytest
        p = DashboardPalette()
        with pytest.raises(Exception):
            p.pastel_blue = "red"  # type: ignore[misc]
