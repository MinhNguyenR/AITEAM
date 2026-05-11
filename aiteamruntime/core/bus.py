from __future__ import annotations

from collections import deque
from queue import Empty, Full, Queue
import threading
from typing import Iterable

from .events import AgentEvent


class EventBus:
    """Thread-safe pub/sub bus with a bounded replay buffer."""

    def __init__(self, *, maxlen: int = 1000) -> None:
        self._buffer: deque[AgentEvent] = deque(maxlen=max(1, int(maxlen)))
        self._subscribers: set[Queue[AgentEvent]] = set()
        self._lock = threading.RLock()

    def publish(self, event: AgentEvent) -> AgentEvent:
        with self._lock:
            self._buffer.append(event)
            subscribers = list(self._subscribers)
        for queue in subscribers:
            try:
                queue.put_nowait(event)
            except Full:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (Empty, Full):
                    pass
        return event

    def replay(self, *, run_id: str | None = None) -> list[AgentEvent]:
        with self._lock:
            events = list(self._buffer)
        if run_id is None:
            return events
        return [event for event in events if event.run_id == run_id]

    def subscribe(
        self,
        *,
        replay: bool = True,
        run_id: str | None = None,
        max_queue: int = 1000,
    ) -> "EventSubscription":
        queue: Queue[AgentEvent] = Queue(maxsize=max(1, int(max_queue)))
        with self._lock:
            self._subscribers.add(queue)
            buffered = list(self._buffer) if replay else []
        for event in buffered:
            if run_id is None or event.run_id == run_id:
                queue.put(event)
        return EventSubscription(self, queue, run_id=run_id)

    def _unsubscribe(self, queue: Queue[AgentEvent]) -> None:
        with self._lock:
            self._subscribers.discard(queue)


class EventSubscription:
    def __init__(
        self,
        bus: EventBus,
        queue: Queue[AgentEvent],
        *,
        run_id: str | None = None,
    ) -> None:
        self._bus = bus
        self._queue = queue
        self._run_id = run_id
        self._closed = False

    def close(self) -> None:
        if not self._closed:
            self._bus._unsubscribe(self._queue)
            self._closed = True

    def __iter__(self) -> Iterable[AgentEvent]:
        return self

    def __next__(self) -> AgentEvent:
        while True:
            if self._closed:
                raise StopIteration
            event = self._queue.get()
            if self._run_id is None or event.run_id == self._run_id:
                return event

    def get(self, timeout: float | None = None) -> AgentEvent | None:
        try:
            event = self._queue.get(timeout=timeout)
        except Empty:
            return None
        if self._run_id is not None and event.run_id != self._run_id:
            return None
        return event
