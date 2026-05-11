from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import threading
from typing import Callable

from .bus import EventBus


class AgentScheduler:
    """Small trigger-based task scheduler for event-driven agents.

    Tracks in-flight task count so the runtime can apply backpressure
    via :meth:`has_capacity` rather than letting the executor's internal
    queue grow without bound.
    """

    def __init__(
        self,
        bus: EventBus | None = None,
        *,
        max_workers: int = 8,
        max_pending_factor: float = 2.0,
    ) -> None:
        self.bus = bus or EventBus()
        self.max_workers = max(1, int(max_workers))
        self.max_pending = max(self.max_workers, int(self.max_workers * max(1.0, float(max_pending_factor))))
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="aitr-")
        self._abort_run_ids: set[str] = set()
        self._pending_lock = threading.Lock()
        self._pending_count = 0

    def request_abort(self, run_id: str, reason: str = "aborted") -> None:
        self._abort_run_ids.add(run_id)

    def is_aborted(self, run_id: str) -> bool:
        return run_id in self._abort_run_ids

    def clear_abort(self, run_id: str) -> None:
        """Drop the abort marker for a run (called during cleanup)."""
        self._abort_run_ids.discard(run_id)

    def has_capacity(self) -> bool:
        """Return False when in-flight + queued tasks would exceed max_pending."""
        with self._pending_lock:
            return self._pending_count < self.max_pending

    def pending_count(self) -> int:
        with self._pending_lock:
            return self._pending_count

    def submit(
        self,
        run_id: str,
        agent_id: str,
        fn: Callable[..., object],
    ) -> Future:
        def _run() -> object:
            try:
                if self.is_aborted(run_id):
                    return None
                try:
                    return fn()
                except Exception as exc:
                    self.bus.publish(
                        AgentEvent(
                            run_id,
                            agent_id,
                            "error",
                            {"type": type(exc).__name__, "message": str(exc)},
                            status="error",
                        )
                    )
                    raise
            finally:
                with self._pending_lock:
                    self._pending_count = max(0, self._pending_count - 1)

        with self._pending_lock:
            self._pending_count += 1
        try:
            return self._executor.submit(_run)
        except RuntimeError:
            # Executor already shut down — undo the pending-count increment
            with self._pending_lock:
                self._pending_count = max(0, self._pending_count - 1)
            raise

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
