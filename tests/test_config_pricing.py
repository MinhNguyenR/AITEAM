"""Tests for core/config/pricing.py — pure helpers."""
import json
import logging
from unittest.mock import patch, MagicMock

from core.config.pricing import (
    _collect_benchmark_scores,
    _numeric_leaves,
    _pick_first,
    fetch_openrouter_pricing,
    sync_live_pricing,
)

_logger = logging.getLogger(__name__)


class TestNumericLeaves:
    def test_flat_dict(self):
        result = _numeric_leaves({"a": 1.0, "b": 2.5})
        assert result == {"a": 1.0, "b": 2.5}

    def test_nested_dict(self):
        result = _numeric_leaves({"outer": {"inner": 3.0}})
        assert result == {"outer.inner": 3.0}

    def test_boolean_excluded(self):
        result = _numeric_leaves({"flag": True})
        assert "flag" not in result

    def test_non_numeric_excluded(self):
        result = _numeric_leaves({"name": "string", "count": 5})
        assert "name" not in result
        assert result["count"] == 5.0

    def test_empty_dict(self):
        result = _numeric_leaves({})
        assert result == {}

    def test_deeply_nested(self):
        result = _numeric_leaves({"l1": {"l2": {"l3": 7.0}}})
        assert result["l1.l2.l3"] == 7.0


class TestCollectBenchmarkScores:
    def test_benchmark_key(self):
        m = {"benchmark": {"mmlu": 0.85, "hellaswag": 0.9}}
        result = _collect_benchmark_scores(m)
        assert "benchmark.mmlu" in result
        assert result["benchmark.mmlu"] == 0.85

    def test_benchmarks_key(self):
        m = {"benchmarks": {"arc": 0.75}}
        result = _collect_benchmark_scores(m)
        assert "benchmarks.arc" in result

    def test_all_numeric_subdicts(self):
        m = {
            "performance": {"speed": 100.0, "quality": 0.9},
            "id": "model-id",  # skipped
        }
        result = _collect_benchmark_scores(m)
        assert "performance.speed" in result
        assert "performance.quality" in result

    def test_skipped_keys(self):
        m = {"id": "x", "pricing": {"input": 1.0}}
        result = _collect_benchmark_scores(m)
        assert not result  # pricing is skipped

    def test_mixed_value_subdict_skipped(self):
        m = {"mixed": {"num": 1.0, "str": "hello"}}
        result = _collect_benchmark_scores(m)
        assert "mixed.num" not in result  # not all-numeric values


class TestPickFirst:
    def test_returns_first_present(self):
        obj = {"b": 2, "c": 3}
        assert _pick_first(obj, ("a", "b", "c")) == 2

    def test_skips_none_values(self):
        obj = {"a": None, "b": 42}
        assert _pick_first(obj, ("a", "b")) == 42

    def test_returns_default_when_not_found(self):
        assert _pick_first({}, ("x", "y"), default="fallback") == "fallback"

    def test_returns_none_default(self):
        assert _pick_first({}, ("x",)) is None


class TestFetchOpenrouterPricing:
    def test_returns_cached_when_already_fetched(self):
        cache = {"model-x": {"input": 1.0, "output": 2.0}}
        result_cache, result_fetched = fetch_openrouter_pricing(
            "sk-key", cache, True, _logger, force=False
        )
        assert result_cache is cache
        assert result_fetched is True

    def test_url_error_returns_unchanged_cache(self):
        import urllib.error
        cache = {}
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result_cache, result_fetched = fetch_openrouter_pricing(
                "sk-key", cache, False, _logger
            )
        assert result_fetched is False

    def test_parses_model_pricing(self):
        data = json.dumps({"data": [
            {"id": "model-a", "pricing": {"prompt": "0.000001", "completion": "0.000002"}}
        ]}).encode()
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = data
        cache = {}
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result_cache, result_fetched = fetch_openrouter_pricing(
                "sk-key", cache, False, _logger
            )
        assert result_fetched is True
        assert "model-a" in result_cache
        assert result_cache["model-a"]["input"] == pytest.approx(1.0, rel=1e-3)

    def test_force_refetch(self):
        import urllib.error
        cache = {"old": {"input": 1.0, "output": 1.0}}
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("err")):
            result_cache, result_fetched = fetch_openrouter_pricing(
                "sk-key", cache, True, _logger, force=True
            )
        # fetching attempted, but URLError → result_fetched unchanged (still True)
        assert result_cache == cache


class TestSyncLivePricing:
    def test_empty_live_prices_noop(self):
        registry = {"AGENT": {"model": "model-x"}}
        sync_live_pricing(registry, {})
        assert "pricing_source" not in registry["AGENT"]

    def test_updates_matching_model(self):
        registry = {"AGENT": {"model": "model-x"}}
        live = {"model-x": {"input": 5.0, "output": 10.0}}
        sync_live_pricing(registry, live)
        assert registry["AGENT"]["pricing"]["input"] == 5.0
        assert registry["AGENT"]["pricing_source"] == "live"

    def test_fallback_for_unknown_model(self):
        registry = {"AGENT": {"model": "unknown-model"}}
        live = {"model-x": {"input": 5.0, "output": 10.0}}
        sync_live_pricing(registry, live)
        assert registry["AGENT"]["pricing_source"] == "config_fallback"


import pytest

from core.config.pricing import fetch_model_detail


class TestFetchModelDetail:
    def _make_response(self, data: dict) -> MagicMock:
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(data).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_returns_empty_on_url_error(self):
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("offline")):
            result = fetch_model_detail("sk-test", "some-model")
        assert result == {}

    def test_returns_empty_when_model_not_in_data(self):
        data = {"data": [{"id": "other-model", "pricing": {}}]}
        mock_resp = self._make_response(data)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_model_detail("sk-test", "missing-model")
        assert result == {}

    def test_returns_detail_for_matching_model(self):
        data = {
            "data": [
                {
                    "id": "target-model",
                    "name": "Target Model",
                    "description": "desc",
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                    "context_length": 128000,
                    "top_provider": {"max_completion_tokens": 4096},
                    "architecture": {"modality": "text"},
                }
            ]
        }
        mock_resp = self._make_response(data)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_model_detail("sk-test", "target-model")

        assert result["id"] == "target-model"
        assert result["input_price_per_1m"] == pytest.approx(1.0)
        assert result["context_length"] == 128000
        assert result["max_completion"] == 4096

    def test_invalid_pricing_defaults_to_zero(self):
        data = {
            "data": [
                {
                    "id": "bad-price-model",
                    "pricing": {"prompt": "NaN", "completion": "invalid"},
                }
            ]
        }
        mock_resp = self._make_response(data)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_model_detail("sk-test", "bad-price-model")

        assert result["input_price_per_1m"] == 0.0
        assert result["output_price_per_1m"] == 0.0

    def test_extra_keys_collected(self):
        data = {
            "data": [
                {
                    "id": "model-x",
                    "pricing": {},
                    "some_extra_field": "value",
                }
            ]
        }
        mock_resp = self._make_response(data)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_model_detail("sk-test", "model-x")
        assert "extra_keys" in result
        assert "some_extra_field" in result["extra_keys"]

    def test_moderation_picked_from_top_provider(self):
        data = {
            "data": [
                {
                    "id": "moderated-model",
                    "pricing": {},
                    "top_provider": {"is_moderated": True},
                }
            ]
        }
        mock_resp = self._make_response(data)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_model_detail("sk-test", "moderated-model")
        assert result["moderation"] is True

    def test_json_decode_error_returns_empty(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not-valid-json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_model_detail("sk-test", "any-model")
        assert result == {}
