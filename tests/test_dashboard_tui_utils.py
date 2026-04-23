"""Tests for core/dashboard/tui/utils.py — pure math/formatting helpers."""
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

sys.modules.setdefault("core.cli.chrome.ui", MagicMock(clear_screen=MagicMock()))

from core.dashboard.tui.utils import default_range, paginate, safe_float, safe_int


class TestDefaultRange:
    def test_returns_tuple_of_datetimes(self):
        since, until = default_range(days=1)
        assert isinstance(since, datetime)
        assert isinstance(until, datetime)

    def test_delta_matches_days(self):
        now = datetime(2024, 6, 1, 12, 0, 0)
        since, until = default_range(days=3, now=now)
        assert until == now
        assert (until - since).days == 3

    def test_zero_days_clamped_to_one(self):
        since, until = default_range(days=0)
        assert (until - since).days >= 1

    def test_negative_days_clamped_to_one(self):
        since, until = default_range(days=-5)
        assert (until - since).days >= 1


class TestPaginate:
    def test_first_page(self):
        items = list(range(10))
        result, page, total = paginate(items, page=0, page_size=3)
        assert result == [0, 1, 2]
        assert page == 0
        assert total == 4  # ceil(10/3)=4

    def test_last_page(self):
        items = list(range(10))
        result, page, total = paginate(items, page=3, page_size=3)
        assert result == [9]

    def test_page_clamped_to_valid(self):
        items = list(range(5))
        result, page, total = paginate(items, page=100, page_size=5)
        assert page == 0
        assert len(result) == 5

    def test_empty_list_returns_empty(self):
        result, page, total = paginate([], page=0, page_size=5)
        assert result == []
        assert total == 1

    def test_exact_page_boundary(self):
        items = list(range(6))
        result, page, total = paginate(items, page=1, page_size=3)
        assert result == [3, 4, 5]
        assert total == 2


class TestSafeInt:
    def test_int(self): assert safe_int(5) == 5
    def test_none(self): assert safe_int(None) == 0
    def test_str(self): assert safe_int("3") == 3
    def test_invalid(self): assert safe_int("x") == 0


class TestSafeFloat:
    def test_float(self): assert safe_float(1.5) == 1.5
    def test_none(self): assert safe_float(None) == 0.0
    def test_invalid(self): assert safe_float("bad") == 0.0
