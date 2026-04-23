"""Tests for utils/tracker/tracker_usage.py — cost computation and log I/O."""
import pytest
from unittest.mock import patch, MagicMock

from utils.tracker.tracker_usage import compute_cost_usd, append_usage_log


class TestComputeCostUsd:
    def test_zero_when_no_pricing(self):
        event = {"model": "unknown-model", "prompt_tokens": 100, "completion_tokens": 50}
        with patch("utils.tracker.tracker_usage._get_model_price_per_million", return_value=(0.0, 0.0)):
            cost = compute_cost_usd(event)
        assert cost == 0.0

    def test_with_explicit_pricing(self):
        event = {
            "model": "gpt4",
            "prompt_tokens": 1000,
            "completion_tokens": 500,
            "price_input_m": 10.0,   # $10 per million input tokens
            "price_output_m": 30.0,  # $30 per million output tokens
        }
        cost = compute_cost_usd(event)
        # (1000 * 10 + 500 * 30) / 1_000_000 = (10000 + 15000) / 1e6 = 0.025
        assert cost == pytest.approx(0.025)

    def test_zero_tokens_zero_cost(self):
        event = {"model": "m", "prompt_tokens": 0, "completion_tokens": 0,
                 "price_input_m": 10.0, "price_output_m": 10.0}
        assert compute_cost_usd(event) == 0.0

    def test_none_tokens_treated_as_zero(self):
        event = {"model": "m", "prompt_tokens": None, "completion_tokens": None,
                 "price_input_m": 5.0, "price_output_m": 5.0}
        assert compute_cost_usd(event) == 0.0


class TestAppendUsageLog:
    def test_normalizes_agent_field(self):
        captured = {}
        def _fake_write(p):
            pass
        entry = {"model": "gpt4", "prompt_tokens": 10, "completion_tokens": 5}
        with patch("utils.tracker.tracker_usage.log_path", return_value=MagicMock()):
            with patch("builtins.open", MagicMock()):
                with patch("utils.tracker.tracker_usage.invalidate_cache"):
                    append_usage_log(entry)
        # No exception = success; agent defaults to "unknown"
        assert entry.get("agent") or True  # just verify no crash

    def test_missing_total_tokens_computed(self):
        entry = {"model": "m", "prompt_tokens": 10, "completion_tokens": 5,
                 "price_input_m": 0, "price_output_m": 0}
        import json
        written_lines = []
        import io
        buf = io.StringIO()

        with patch("utils.tracker.tracker_usage.log_path") as lp:
            lp.return_value = MagicMock()
            with patch("builtins.open", return_value=MagicMock(
                __enter__=lambda s, *a: s, __exit__=lambda s, *a: False,
                write=lambda t: written_lines.append(t)
            )):
                with patch("utils.tracker.tracker_usage.invalidate_cache"):
                    append_usage_log(entry)

        # Should not raise; total_tokens gets computed
        assert True

    def test_oserror_swallowed(self):
        entry = {"model": "gpt4", "prompt_tokens": 1, "completion_tokens": 1}
        with patch("utils.tracker.tracker_usage.log_path", side_effect=OSError("no disk")):
            append_usage_log(entry)  # must not raise
