"""Shared bounded thread pool for monitor commands.

Each interactive monitor action (ask, btw, gate accept, check accept,
explainer, task clear) used to spawn a fresh ``threading.Thread(daemon=True)``.
That works for one-off clicks but accumulates idle threads if a hung
network call never returns, and provides no central place to enforce a
concurrency cap or shut things down when the TUI closes.

This module exposes a single shared :class:`concurrent.futures.ThreadPoolExecutor`
with a small worker count and an ``atexit`` shutdown hook. Callers
should use :func:`submit_monitor_task` instead of starting raw threads.
"""

from __future__ import annotations

import atexit
import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable

logger = logging.getLogger(__name__)

_MAX_WORKERS = 4
_pool_lock = threading.Lock()
_pool: ThreadPoolExecutor | None = None
_shutdown_registered = False


def _ensure_pool() -> ThreadPoolExecutor:
    global _pool, _shutdown_registered
    with _pool_lock:
        if _pool is None:
            _pool = ThreadPoolExecutor(
                max_workers=_MAX_WORKERS,
                thread_name_prefix="monitor-task",
            )
            if not _shutdown_registered:
                atexit.register(shutdown_monitor_tasks)
                _shutdown_registered = True
        return _pool


def submit_monitor_task(fn: Callable[[], Any]) -> Future:
    """Run ``fn`` on the shared monitor task pool. Exceptions are logged.

    The pool keeps a fixed number of background workers so a flood of
    user clicks (or a hung handler) can't spawn unbounded threads.
    """

    def _runner() -> Any:
        try:
            return fn()
        except Exception as exc:
            logger.warning("monitor task failed: %s", exc, exc_info=True)
            return None

    return _ensure_pool().submit(_runner)


def shutdown_monitor_tasks() -> None:
    """Stop the pool and cancel any queued work. Called at process exit."""
    global _pool
    with _pool_lock:
        pool = _pool
        _pool = None
    if pool is not None:
        pool.shutdown(wait=False, cancel_futures=True)


__all__ = ["submit_monitor_task", "shutdown_monitor_tasks"]
