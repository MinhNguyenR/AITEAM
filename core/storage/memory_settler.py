from __future__ import annotations

import atexit
import os
import threading
import time
from collections import defaultdict


class MemorySettler:
    def __init__(self, *, idle_seconds: float | None = None) -> None:
        self.idle_seconds = float(idle_seconds if idle_seconds is not None else os.getenv("AI_TEAM_SETTLE_IDLE_SECONDS") or 360)
        self._lock = threading.RLock()
        self._timers: dict[str, threading.Timer] = {}
        self._last_active: dict[str, float] = {}
        self._convo_locks: dict[str, threading.Lock] = defaultdict(threading.Lock)

    def reset(self, convo_id: str) -> None:
        if not convo_id:
            return
        with self._lock:
            self._last_active[convo_id] = time.time()
            old = self._timers.pop(convo_id, None)
            if old is not None:
                old.cancel()
            timer = threading.Timer(self.idle_seconds, self._fire, args=(convo_id,))
            timer.daemon = True
            self._timers[convo_id] = timer
            timer.start()

    def _fire(self, convo_id: str) -> None:
        with self._lock:
            last = self._last_active.get(convo_id, 0)
        if time.time() - last < self.idle_seconds:
            return
        self.force_settle(convo_id)

    def force_settle(self, convo_id: str) -> None:
        lock = self._convo_locks[convo_id]
        if not lock.acquire(blocking=False):
            return
        try:
            from core.storage.memory_coordinator import MemoryCoordinator

            MemoryCoordinator(settler=self).force_settle(convo_id)
        finally:
            lock.release()

    def flush_all(self) -> None:
        if os.getenv("AI_TEAM_SETTLE_ON_EXIT_WITH_MODEL", "").strip().lower() not in {"1", "true", "yes", "on"}:
            return
        with self._lock:
            ids = list(self._last_active)
        for convo_id in ids:
            self.force_settle(convo_id)


_SETTLER: MemorySettler | None = None


def get_settler() -> MemorySettler:
    global _SETTLER
    if _SETTLER is None:
        _SETTLER = MemorySettler()
        atexit.register(_SETTLER.flush_all)
    return _SETTLER
