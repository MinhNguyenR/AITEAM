"""In-process TTL cache for tracker reads."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_TTL_SECONDS = 12.0
_CACHE_LAST: dict[str, tuple[float, Any]] = {}


def cache_get(key: str) -> Any:
    now = time.monotonic()
    item = _CACHE_LAST.get(key)
    if not item:
        return None
    ts, value = item
    if now - ts > _CACHE_TTL_SECONDS:
        _CACHE_LAST.pop(key, None)
        return None
    return value


def cache_set(key: str, value: Any) -> Any:
    _CACHE_LAST[key] = (time.monotonic(), value)
    return value


def invalidate_cache(prefix: str | None = None) -> None:
    if prefix is None:
        cleared = len(_CACHE_LAST)
        _CACHE_LAST.clear()
        if cleared:
            logger.info("[Tracker] cache cleared (%s entries)", cleared)
        return
    cleared = 0
    for key in list(_CACHE_LAST):
        if key.startswith(prefix):
            _CACHE_LAST.pop(key, None)
            cleared += 1
    if cleared:
        logger.info("[Tracker] cache cleared prefix=%s (%s entries)", prefix, cleared)
