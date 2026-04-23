"""Tests for summarize_tokens_by_cli_batches in tracker_batches.py."""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

from utils.tracker.tracker_batches import summarize_tokens_by_cli_batches


def _ts(dt: datetime) -> str:
    return dt.isoformat()


def _make_batch(ts: datetime, mode: str = "ask", prompt: str = "test") -> dict:
    return {"kind": "cli_batch", "timestamp": _ts(ts), "mode": mode, "prompt": prompt}


def _make_row(ts: datetime, pt: int = 100, ct: int = 50, cost: float = 0.001,
              model: str = "model-x", role: str = "LEADER") -> dict:
    return {
        "timestamp": _ts(ts),
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "cost_usd": cost,
        "model": model,
        "role_key": role,
    }


class TestSummarizeTokensByCliBatches:
    def test_empty_batches_returns_empty(self):
        since = datetime(2026, 1, 1)
        until = datetime(2026, 1, 2)
        with patch("utils.tracker.tracker_batches.read_cli_batches_tail", return_value=[]), \
             patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v):
            result = summarize_tokens_by_cli_batches(since, until)
        assert result == []

    def test_returns_cached_value(self):
        since = datetime(2026, 1, 1)
        until = datetime(2026, 1, 2)
        cached = [{"batch_idx": 1, "mode": "ask"}]
        with patch("utils.tracker.tracker_batches.cache_get", return_value=cached):
            result = summarize_tokens_by_cli_batches(since, until)
        assert result is cached

    def test_single_batch_with_usage_rows(self):
        since = datetime(2026, 1, 1, 10, 0, 0)
        until = datetime(2026, 1, 1, 18, 0, 0)
        batch_ts = datetime(2026, 1, 1, 11, 0, 0)
        row_ts = datetime(2026, 1, 1, 12, 0, 0)

        batches = [_make_batch(batch_ts, mode="ask")]
        rows = [_make_row(row_ts, pt=200, ct=100, cost=0.005)]

        with patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v), \
             patch("utils.tracker.tracker_batches.read_cli_batches_tail", return_value=batches), \
             patch("utils.tracker.tracker_batches.read_usage_rows_timerange", return_value=rows):
            result = summarize_tokens_by_cli_batches(since, until)

        assert len(result) == 1
        assert result[0]["batch_idx"] == 1
        assert result[0]["mode"] == "ask"
        assert "by_model" in result[0]
        assert "by_role" in result[0]
        assert "totals" in result[0]

    def test_multiple_batches_partitioned(self):
        since = datetime(2026, 1, 1, 9, 0, 0)
        until = datetime(2026, 1, 1, 18, 0, 0)
        b1_ts = datetime(2026, 1, 1, 10, 0, 0)
        b2_ts = datetime(2026, 1, 1, 13, 0, 0)
        r1_ts = datetime(2026, 1, 1, 11, 0, 0)  # belongs to batch1
        r2_ts = datetime(2026, 1, 1, 14, 0, 0)  # belongs to batch2

        batches = [_make_batch(b1_ts, mode="ask"), _make_batch(b2_ts, mode="change")]
        rows = [
            _make_row(r1_ts, pt=100, ct=50, model="model-a", role="LEADER"),
            _make_row(r2_ts, pt=200, ct=80, model="model-b", role="EXPERT"),
        ]

        with patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v), \
             patch("utils.tracker.tracker_batches.read_cli_batches_tail", return_value=batches), \
             patch("utils.tracker.tracker_batches.read_usage_rows_timerange", return_value=rows):
            result = summarize_tokens_by_cli_batches(since, until)

        assert len(result) == 2
        # First batch should have model-a row
        assert "model-a" in result[0]["by_model"]
        # Second batch should have model-b row
        assert "model-b" in result[1]["by_model"]

    def test_batch_outside_range_excluded(self):
        since = datetime(2026, 1, 1)
        until = datetime(2026, 1, 2)
        # batch timestamp is outside [since, until]
        batches = [_make_batch(datetime(2025, 12, 30, 10, 0, 0))]

        with patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v), \
             patch("utils.tracker.tracker_batches.read_cli_batches_tail", return_value=batches), \
             patch("utils.tracker.tracker_batches.read_usage_rows_timerange", return_value=[]):
            result = summarize_tokens_by_cli_batches(since, until)

        assert result == []

    def test_batch_with_invalid_timestamp_skipped(self):
        since = datetime(2026, 1, 1)
        until = datetime(2026, 1, 2)
        batches = [
            {"kind": "cli_batch", "timestamp": "not-a-timestamp", "mode": "ask", "prompt": "x"},
            _make_batch(datetime(2026, 1, 1, 12, 0, 0)),
        ]

        with patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v), \
             patch("utils.tracker.tracker_batches.read_cli_batches_tail", return_value=batches), \
             patch("utils.tracker.tracker_batches.read_usage_rows_timerange", return_value=[]):
            result = summarize_tokens_by_cli_batches(since, until)

        # invalid-ts batch filtered by parse_usage_timestamp
        assert isinstance(result, list)

    def test_cost_usd_summed_correctly(self):
        since = datetime(2026, 1, 1, 9, 0, 0)
        until = datetime(2026, 1, 1, 18, 0, 0)
        b_ts = datetime(2026, 1, 1, 10, 0, 0)
        rows = [
            _make_row(datetime(2026, 1, 1, 11, 0, 0), cost=0.002),
            _make_row(datetime(2026, 1, 1, 12, 0, 0), cost=0.003),
        ]
        batches = [_make_batch(b_ts)]

        with patch("utils.tracker.tracker_batches.cache_get", return_value=None), \
             patch("utils.tracker.tracker_batches.cache_set", side_effect=lambda k, v: v), \
             patch("utils.tracker.tracker_batches.read_cli_batches_tail", return_value=batches), \
             patch("utils.tracker.tracker_batches.read_usage_rows_timerange", return_value=rows):
            result = summarize_tokens_by_cli_batches(since, until)

        assert abs(result[0]["cost_usd"] - 0.005) < 1e-6
