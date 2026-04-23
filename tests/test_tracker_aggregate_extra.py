"""Tests for utils/tracker/tracker_aggregate.py — period summaries and stats."""
from datetime import date
from unittest.mock import patch

from utils.tracker.tracker_aggregate import (
    aggregate_usage_by_role,
    build_usage_summary,
    get_local_stats,
    get_period_usage,
    rows_for_summary_period,
)
from utils.tracker.tracker_cache import _CACHE_LAST


def _clear_cache():
    _CACHE_LAST.clear()


def _rows():
    return [
        {"role_key": "AMBASSADOR", "model": "claude-3-haiku", "total_tokens": 100, "cost_usd": 0.001,
         "timestamp": "2024-06-01T10:00:00"},
        {"role_key": "LEADER", "model": "claude-3-sonnet", "total_tokens": 200, "cost_usd": 0.002,
         "timestamp": "2024-06-02T11:00:00"},
        {"role_key": "AMBASSADOR", "model": "claude-3-haiku", "total_tokens": 50, "cost_usd": 0.0005,
         "timestamp": "2024-06-03T09:00:00"},
    ]


class TestRowsForSummaryPeriod:
    def test_returns_all_rows_for_session(self):
        _clear_cache()
        rows = _rows()
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=rows), \
             patch("utils.tracker.tracker_aggregate.cache_get", return_value=None), \
             patch("utils.tracker.tracker_aggregate.cache_set", side_effect=lambda k, v: v):
            result = rows_for_summary_period("session")
        assert len(result) == 3

    def test_returns_empty_when_no_rows(self):
        _clear_cache()
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=[]), \
             patch("utils.tracker.tracker_aggregate.cache_get", return_value=None), \
             patch("utils.tracker.tracker_aggregate.cache_set", side_effect=lambda k, v: v):
            result = rows_for_summary_period("session")
        assert result == []

    def test_returns_cached_value(self):
        cached = [{"role_key": "X", "total_tokens": 5, "cost_usd": 0.0, "timestamp": ""}]
        with patch("utils.tracker.tracker_aggregate.cache_get", return_value=cached):
            result = rows_for_summary_period("session")
        assert result == cached

    def test_today_filter(self):
        _clear_cache()
        today_ts = date.today().isoformat() + "T10:00:00"
        old_ts = "2020-01-01T10:00:00"
        rows = [
            {"role_key": "A", "total_tokens": 10, "cost_usd": 0.0, "timestamp": today_ts},
            {"role_key": "B", "total_tokens": 20, "cost_usd": 0.0, "timestamp": old_ts},
        ]
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=rows), \
             patch("utils.tracker.tracker_aggregate.cache_get", return_value=None), \
             patch("utils.tracker.tracker_aggregate.cache_set", side_effect=lambda k, v: v):
            result = rows_for_summary_period("today")
        assert len(result) == 1
        assert result[0]["role_key"] == "A"


class TestBuildUsageSummary:
    def test_basic_summary(self):
        _clear_cache()
        with patch("utils.tracker.tracker_aggregate.rows_for_summary_period", return_value=_rows()), \
             patch("utils.tracker.tracker_aggregate.cache_get", return_value=None), \
             patch("utils.tracker.tracker_aggregate.cache_set", side_effect=lambda k, v: v):
            result = build_usage_summary("session")
        assert result["total_requests"] == 3
        assert result["total_tokens"] == 350
        assert "by_role" in result

    def test_returns_cached(self):
        cached = {"period": "session", "total_requests": 99}
        with patch("utils.tracker.tracker_aggregate.cache_get", return_value=cached):
            result = build_usage_summary("session")
        assert result == cached


class TestGetLocalStats:
    def test_empty_when_no_rows(self):
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=[]):
            result = get_local_stats()
        assert result["total_requests"] == 0
        assert result["by_agent"] == {}

    def test_basic_stats(self):
        rows = _rows()
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=rows):
            result = get_local_stats(for_today=False)
        assert result["total_requests"] == 3
        assert "AMBASSADOR" in result["by_agent"]
        assert result["by_agent"]["AMBASSADOR"]["requests"] == 2

    def test_today_filter(self):
        today_ts = date.today().isoformat() + "T10:00:00"
        rows = [
            {"role_key": "A", "model": "m1", "total_tokens": 10, "cost_usd": 0.0, "timestamp": today_ts},
            {"role_key": "B", "model": "m2", "total_tokens": 20, "cost_usd": 0.0, "timestamp": "2020-01-01T10:00:00"},
        ]
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=rows):
            result = get_local_stats(for_today=True)
        assert result["total_requests"] == 1
        assert "A" in result["by_agent"]


class TestGetPeriodUsage:
    def test_structure(self):
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=[]):
            result = get_period_usage()
        assert "daily" in result
        assert "monthly" in result
        assert "yearly" in result

    def test_today_row_counted(self):
        today_ts = date.today().isoformat() + "T10:00:00"
        rows = [{"total_tokens": 100, "cost_usd": 0.001, "timestamp": today_ts}]
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=rows):
            result = get_period_usage()
        assert result["daily"]["requests"] == 1
        assert result["monthly"]["requests"] == 1

    def test_old_row_not_in_daily(self):
        old_ts = "2020-01-01T10:00:00"
        rows = [{"total_tokens": 100, "cost_usd": 0.001, "timestamp": old_ts}]
        with patch("utils.tracker.tracker_aggregate.read_usage_log", return_value=rows):
            result = get_period_usage()
        assert result["daily"]["requests"] == 0
