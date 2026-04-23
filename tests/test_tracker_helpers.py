"""Tests for utils/tracker/tracker_helpers.py — pure parsing/math helpers."""
import os
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from utils.tracker.tracker_helpers import (
    normalize_iso,
    parse_day,
    parse_usage_timestamp,
    read_last_n_line_strings,
    safe_float,
    safe_int,
    token_io_totals,
)


class TestSafeInt:
    def test_normal_int(self): assert safe_int(5) == 5
    def test_float_truncates(self): assert safe_int(3.9) == 3
    def test_string_int(self): assert safe_int("7") == 7
    def test_none_returns_zero(self): assert safe_int(None) == 0
    def test_empty_string_zero(self): assert safe_int("") == 0
    def test_invalid_string_zero(self): assert safe_int("abc") == 0
    def test_zero_stays_zero(self): assert safe_int(0) == 0


class TestSafeFloat:
    def test_normal_float(self): assert safe_float(1.5) == 1.5
    def test_string_float(self): assert safe_float("2.5") == 2.5
    def test_none_zero(self): assert safe_float(None) == 0.0
    def test_empty_zero(self): assert safe_float("") == 0.0
    def test_invalid_zero(self): assert safe_float("xyz") == 0.0
    def test_int_converts(self): assert safe_float(3) == 3.0


class TestNormalizeIso:
    def test_returns_string_unchanged(self):
        ts = "2024-01-15T12:00:00"
        assert normalize_iso(ts) == ts

    def test_none_returns_now(self):
        result = normalize_iso(None)
        assert "T" in result  # ISO format with time component

    def test_empty_string_returns_now(self):
        result = normalize_iso("")
        assert "T" in result


class TestParseDay:
    def test_iso_date(self):
        d = parse_day("2024-01-15T12:00:00")
        assert d == date(2024, 1, 15)

    def test_date_only(self):
        d = parse_day("2024-03-20")
        assert d == date(2024, 3, 20)

    def test_z_suffix(self):
        d = parse_day("2024-06-01T00:00:00Z")
        assert d == date(2024, 6, 1)

    def test_empty_returns_none(self):
        assert parse_day("") is None

    def test_invalid_returns_none(self):
        assert parse_day("not-a-date") is None

    def test_none_returns_none(self):
        assert parse_day(None) is None


class TestParseUsageTimestamp:
    def test_valid_iso(self):
        result = parse_usage_timestamp("2024-01-15T10:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_none_returns_none(self):
        assert parse_usage_timestamp(None) is None

    def test_invalid_returns_none(self):
        assert parse_usage_timestamp("garbage") is None


class TestTokenIoTotals:
    def test_sums_tokens(self):
        rows = [
            {"prompt_tokens": 100, "completion_tokens": 50},
            {"prompt_tokens": 200, "completion_tokens": 75},
        ]
        result = token_io_totals(rows)
        assert result["prompt_tokens"] == 300
        assert result["completion_tokens"] == 125
        assert result["total_tokens"] == 425

    def test_empty_rows(self):
        result = token_io_totals([])
        assert result == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def test_missing_keys_treated_as_zero(self):
        rows = [{"prompt_tokens": 10}]
        result = token_io_totals(rows)
        assert result["completion_tokens"] == 0
        assert result["total_tokens"] == 10


class TestReadLastNLineStrings:
    def test_reads_last_n_lines(self, tmp_path):
        f = tmp_path / "log.jsonl"
        # No trailing newline so last non-empty line is returned
        f.write_text("line1\nline2\nline3\nline4", encoding="utf-8")
        result = read_last_n_line_strings(f, 2)
        assert "line4" in result

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.jsonl"
        f.write_bytes(b"")
        result = read_last_n_line_strings(f, 5)
        assert result == []

    def test_missing_file_returns_empty(self, tmp_path):
        result = read_last_n_line_strings(tmp_path / "missing.jsonl", 5)
        assert result == []

    def test_request_more_than_available(self, tmp_path):
        f = tmp_path / "log.jsonl"
        f.write_text("a\nb\n", encoding="utf-8")
        result = read_last_n_line_strings(f, 10)
        assert len(result) == 2
