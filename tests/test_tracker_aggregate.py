"""Tests for utils/tracker/tracker_aggregate.py — pure aggregation helpers."""
import pytest
from unittest.mock import patch

from utils.tracker.tracker_aggregate import (
    aggregate_rows_by_role_model,
    aggregate_usage_by_role,
    search_model_substring,
)


def _row(role="Leader", model="gpt-4", tokens=100, cost=0.01):
    return {"role_key": role, "model": model, "total_tokens": tokens, "cost_usd": cost}


class TestAggregateRowsByRoleModel:
    def test_groups_by_role_model(self):
        rows = [_row("Leader", "gpt4"), _row("Leader", "gpt4"), _row("Worker", "gpt4")]
        result = aggregate_rows_by_role_model(rows)
        leader_entry = next(r for r in result if r["role"] == "Leader")
        assert leader_entry["requests"] == 2
        assert leader_entry["tokens"] == 200

    def test_sums_cost(self):
        rows = [_row("A", "m", cost=0.01), _row("A", "m", cost=0.02)]
        result = aggregate_rows_by_role_model(rows)
        assert result[0]["cost"] == pytest.approx(0.03)

    def test_empty_returns_empty(self):
        assert aggregate_rows_by_role_model([]) == []

    def test_sorted_by_tokens_desc(self):
        rows = [_row("A", "m", tokens=10), _row("B", "m", tokens=100)]
        result = aggregate_rows_by_role_model(rows)
        assert result[0]["tokens"] == 100

    def test_unknown_role_fallback(self):
        rows = [{"model": "gpt", "total_tokens": 5, "cost_usd": 0.0}]
        result = aggregate_rows_by_role_model(rows)
        assert result[0]["role"] == "unknown"


class TestSearchModelSubstring:
    def test_matches_substring(self):
        rows = [_row("A", "gpt-4-turbo"), _row("B", "claude-3")]
        result = search_model_substring(rows, "gpt")
        assert len(result) == 1
        assert result[0]["model"] == "gpt-4-turbo"

    def test_empty_needle_returns_empty(self):
        rows = [_row("A", "gpt-4")]
        assert search_model_substring(rows, "") == []

    def test_case_insensitive(self):
        rows = [_row("A", "GPT-4-TURBO")]
        result = search_model_substring(rows, "gpt")
        assert len(result) == 1

    def test_no_match_returns_empty(self):
        rows = [_row("A", "claude")]
        assert search_model_substring(rows, "gpt") == []

    def test_sums_across_same_model(self):
        rows = [_row("A", "gpt", tokens=10), _row("A", "gpt", tokens=20)]
        result = search_model_substring(rows, "gpt")
        assert result[0]["tokens"] == 30


class TestAggregateUsageByRole:
    def test_groups_by_role(self):
        rows = [_row("Leader", "m", tokens=50), _row("Leader", "m", tokens=50)]
        result = aggregate_usage_by_role(rows)
        assert "Leader" in result
        assert result["Leader"]["requests"] == 2
        assert result["Leader"]["tokens"] == 100

    def test_empty_rows_empty_result(self):
        assert aggregate_usage_by_role([]) == {}

    def test_multiple_roles(self):
        rows = [_row("A"), _row("B")]
        result = aggregate_usage_by_role(rows)
        assert "A" in result and "B" in result
