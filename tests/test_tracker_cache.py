"""Tests for utils/tracker/tracker_cache.py — in-process TTL cache."""
import time
from unittest.mock import patch

from utils.tracker.tracker_cache import (
    _CACHE_LAST,
    cache_get,
    cache_set,
    invalidate_cache,
)


def _clear():
    _CACHE_LAST.clear()


class TestCacheGetSet:
    def test_miss_returns_none(self):
        _clear()
        assert cache_get("no_such_key_xyz") is None

    def test_set_then_get(self):
        _clear()
        cache_set("k1", [1, 2, 3])
        assert cache_get("k1") == [1, 2, 3]

    def test_set_returns_value(self):
        _clear()
        result = cache_set("k2", {"a": 1})
        assert result == {"a": 1}

    def test_expired_entry_returns_none(self):
        _clear()
        cache_set("k3", "value")
        # Fake that entry is older than TTL
        ts, val = _CACHE_LAST["k3"]
        _CACHE_LAST["k3"] = (ts - 100.0, val)
        assert cache_get("k3") is None
        assert "k3" not in _CACHE_LAST

    def test_fresh_entry_still_valid(self):
        _clear()
        cache_set("k4", 42)
        assert cache_get("k4") == 42

    def test_overwrite_key(self):
        _clear()
        cache_set("k5", "first")
        cache_set("k5", "second")
        assert cache_get("k5") == "second"


class TestInvalidateCache:
    def test_clear_all(self):
        _clear()
        cache_set("a:1", 1)
        cache_set("b:2", 2)
        invalidate_cache(None)
        assert cache_get("a:1") is None
        assert cache_get("b:2") is None

    def test_clear_by_prefix(self):
        _clear()
        cache_set("cli_batches:x", "v1")
        cache_set("cli_batches:y", "v2")
        cache_set("other:z", "v3")
        invalidate_cache("cli_batches:")
        assert cache_get("cli_batches:x") is None
        assert cache_get("cli_batches:y") is None
        assert cache_get("other:z") == "v3"

    def test_clear_prefix_no_match(self):
        _clear()
        cache_set("foo:1", 10)
        invalidate_cache("bar:")
        assert cache_get("foo:1") == 10

    def test_clear_empty_cache(self):
        _clear()
        invalidate_cache(None)  # should not raise
        invalidate_cache("prefix:")  # should not raise
