"""Node-level resource lock manager with DAG awareness and deadlock detection.

The runtime is event-driven, so any lock acquired by one role must be
released for another role to make progress. ``LockManager`` provides:

* **Mutual exclusion** keyed by free-form resource strings (e.g. file paths).
* **Per-run isolation** — one node holding ``"workspace/foo.py"`` in run A
  does not block run B.
* **DAG dependencies** declared by callers (``depends_on``) — the lock
  manager doesn't enforce these directly, but tracks them so the wait-for
  graph can include both resource contention and structural dependencies.
* **Deadlock detection** via DFS over the wait-for graph. When a cycle is
  found a *victim* is selected by ascending cost score and rejected with
  status ``deadlock``; the others remain queued.
* **Lock timeouts** so a stuck handler can never park another agent forever.

Cost score (lower = more likely to be picked as victim)::

    score = (attempt * W_ATTEMPT) + (waited_total_seconds * W_WAIT) - (priority * W_PRIO)

Defaults: ``W_ATTEMPT=10``, ``W_WAIT=1.0``, ``W_PRIO=5``. The intent is that
a node that has *already* lost the race many times is protected from
starvation while a fresh, low-priority request is the natural sacrifice.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Iterable

logger = logging.getLogger(__name__)

W_ATTEMPT = 10.0
W_WAIT = 1.0
W_PRIO = 5.0


@dataclass(frozen=True)
class LockRequest:
    run_id: str
    node_id: str
    resources: frozenset[str]
    timeout: float = 30.0
    attempt: int = 1
    priority: int = 0
    waited_total_ms: int = 0
    depends_on: frozenset[str] = frozenset()
    requested_at: float = field(default_factory=time.time)

    def cost_score(self) -> float:
        return (
            self.attempt * W_ATTEMPT
            + (self.waited_total_ms / 1000.0) * W_WAIT
            - self.priority * W_PRIO
        )


@dataclass
class LockHandle:
    run_id: str
    node_id: str
    resources: frozenset[str]
    expires_at: float


class LockBlocked(Exception):
    """Raised when a lock cannot be granted (timeout, deadlock, manager closed)."""

    def __init__(
        self,
        *,
        reason: str,
        owner_node_id: str = "",
        contested: Iterable[str] = (),
    ) -> None:
        super().__init__(reason)
        self.reason = reason
        self.owner_node_id = owner_node_id
        self.contested = frozenset(contested)


@dataclass
class _Waiter:
    request: LockRequest
    event: threading.Event = field(default_factory=threading.Event)
    granted: LockHandle | None = None
    rejected: LockBlocked | None = None
    enqueued_at: float = field(default_factory=time.monotonic)


class LockManager:
    """Coordinate node-level resource locks across a single AgentRuntime.

    Lock keys are namespaced by ``run_id`` so concurrent runs don't share
    contention. Resources within a request are atomic — either all are
    acquired or the request waits.
    """

    def __init__(self, *, sweep_interval: float = 1.0) -> None:
        self._lock = threading.RLock()
        self._cv = threading.Condition(self._lock)
        # (run_id, resource) -> node_id holding it
        self._locked: dict[tuple[str, str], str] = {}
        # (run_id, node_id) -> active LockHandle
        self._handles: dict[tuple[str, str], LockHandle] = {}
        # (run_id, node_id) -> _Waiter (only one pending request per node at a time)
        self._waiters: dict[tuple[str, str], _Waiter] = {}
        self._closed = False
        self._sweep_interval = max(0.2, float(sweep_interval))
        self._stop = threading.Event()
        self._sweeper: threading.Thread | None = None
        self._start_sweeper()

    # ── Public API ────────────────────────────────────────────────────────

    def try_acquire(self, request: LockRequest) -> LockHandle | None:
        """Non-blocking acquire — returns a handle or ``None`` if unavailable."""
        with self._lock:
            if self._closed:
                raise LockBlocked(reason="lock manager closed")
            if self._can_acquire_locked(request):
                return self._claim_locked(request)
            return None

    def acquire(self, request: LockRequest) -> LockHandle:
        """Blocking acquire — waits up to ``request.timeout`` seconds.

        Raises :class:`LockBlocked` on timeout or when this request was chosen
        as the deadlock victim.
        """
        with self._lock:
            if self._closed:
                raise LockBlocked(reason="lock manager closed")
            if self._can_acquire_locked(request):
                return self._claim_locked(request)

            # Enqueue this request as a waiter for the contested resources.
            key = (request.run_id, request.node_id)
            existing = self._waiters.get(key)
            if existing is not None:
                # Reject the prior waiter so callers can't double-park a node.
                existing.rejected = LockBlocked(reason="superseded by new request")
                existing.event.set()
            waiter = _Waiter(request)
            self._waiters[key] = waiter

            # Run deadlock detection now — fresh waiters might close a cycle.
            cycle = self._detect_cycle_locked()
            if cycle:
                victim_key = self._choose_victim_locked(cycle)
                if victim_key == key:
                    self._waiters.pop(key, None)
                    # Release the victim's *existing* locks too so the other
                    # cycle members can finally proceed.
                    self._evict_holder_locked(key)
                    self._try_promote_waiters_locked()
                    raise LockBlocked(
                        reason="deadlock",
                        owner_node_id=self._first_owner_locked(request),
                        contested=request.resources,
                    )
                # Victim is someone else: reject their pending request AND
                # release their currently-held locks so the cycle is broken.
                self._reject_waiter_locked(victim_key, reason="deadlock-victim")
                self._evict_holder_locked(victim_key)
                self._try_promote_waiters_locked()

        # Wait outside the lock.
        granted = waiter.event.wait(timeout=request.timeout)
        with self._lock:
            self._waiters.pop((request.run_id, request.node_id), None)
            if waiter.rejected is not None:
                raise waiter.rejected
            if not granted:
                raise LockBlocked(
                    reason="timeout",
                    owner_node_id=self._first_owner_locked(request),
                    contested=request.resources,
                )
            assert waiter.granted is not None
            return waiter.granted

    def release(self, handle: LockHandle) -> None:
        """Release a previously-acquired handle. Idempotent."""
        with self._lock:
            stored = self._handles.pop((handle.run_id, handle.node_id), None)
            if stored is None:
                return
            for resource in stored.resources:
                if self._locked.get((handle.run_id, resource)) == handle.node_id:
                    self._locked.pop((handle.run_id, resource), None)
            self._try_promote_waiters_locked()

    def handle_for(self, run_id: str, node_id: str) -> LockHandle | None:
        """Return the active handle for a node, if it currently owns one."""
        with self._lock:
            return self._handles.get((run_id, node_id))

    def release_node(self, run_id: str, node_id: str) -> bool:
        """Release locks held by a node. Returns True if a handle was present."""
        handle = self.handle_for(run_id, node_id)
        if handle is None:
            return False
        self.release(handle)
        return True

    def release_run(self, run_id: str) -> None:
        """Drop all locks and waiters belonging to a run (called on cleanup)."""
        with self._lock:
            for key in list(self._handles):
                if key[0] == run_id:
                    self._handles.pop(key, None)
            for key in list(self._locked):
                if key[0] == run_id:
                    self._locked.pop(key, None)
            for key in list(self._waiters):
                if key[0] == run_id:
                    self._reject_waiter_locked(key, reason="run cleaned up")
            self._try_promote_waiters_locked()

    def snapshot(self) -> dict[str, list[dict]]:
        """Debug helper: return a static view of held locks and waiters."""
        with self._lock:
            held = [
                {"run_id": rid, "node_id": nid, "resources": sorted(h.resources), "expires_at": h.expires_at}
                for (rid, nid), h in self._handles.items()
            ]
            waiting = [
                {
                    "run_id": w.request.run_id,
                    "node_id": w.request.node_id,
                    "resources": sorted(w.request.resources),
                    "attempt": w.request.attempt,
                    "score": w.request.cost_score(),
                }
                for w in self._waiters.values()
            ]
            return {"held": held, "waiting": waiting}

    def shutdown(self) -> None:
        self._stop.set()
        with self._lock:
            self._closed = True
            for key in list(self._waiters):
                self._reject_waiter_locked(key, reason="lock manager shutdown")
            self._handles.clear()
            self._locked.clear()
        if self._sweeper is not None and self._sweeper.is_alive():
            self._sweeper.join(timeout=2.0)
        self._sweeper = None

    # ── Internals (require ``_lock`` held) ─────────────────────────────────

    def _can_acquire_locked(self, request: LockRequest) -> bool:
        for resource in request.resources:
            owner = self._locked.get((request.run_id, resource))
            if owner is not None and owner != request.node_id:
                return False
        return True

    def _claim_locked(self, request: LockRequest) -> LockHandle:
        expires_at = time.time() + max(0.5, float(request.timeout))
        handle = LockHandle(
            run_id=request.run_id,
            node_id=request.node_id,
            resources=request.resources,
            expires_at=expires_at,
        )
        for resource in request.resources:
            self._locked[(request.run_id, resource)] = request.node_id
        self._handles[(request.run_id, request.node_id)] = handle
        return handle

    def _first_owner_locked(self, request: LockRequest) -> str:
        for resource in request.resources:
            owner = self._locked.get((request.run_id, resource))
            if owner:
                return owner
        return ""

    def _detect_cycle_locked(self) -> list[tuple[str, str]] | None:
        """DFS the wait-for graph; return the first cycle found or ``None``.

        Edges go from a *waiter* node to the *holder* of any resource it's
        waiting on. A cycle means each node in the loop is blocked on the
        next, which can never resolve without intervention.
        """
        # Build adjacency: waiter (run_id, node_id) -> set of (run_id, holder_node_id)
        graph: dict[tuple[str, str], set[tuple[str, str]]] = defaultdict(set)
        for waiter_key, waiter in self._waiters.items():
            run_id = waiter.request.run_id
            for resource in waiter.request.resources:
                owner = self._locked.get((run_id, resource))
                if owner and owner != waiter_key[1]:
                    graph[waiter_key].add((run_id, owner))

        # Standard DFS cycle detection (white/gray/black colouring).
        WHITE, GRAY, BLACK = 0, 1, 2
        color: dict[tuple[str, str], int] = defaultdict(lambda: WHITE)

        def dfs(start: tuple[str, str]) -> list[tuple[str, str]] | None:
            stack: list[tuple[tuple[str, str], list[tuple[str, str]]]] = [(start, [start])]
            while stack:
                node, path = stack[-1]
                color[node] = GRAY
                neighbour: tuple[str, str] | None = None
                for nb in graph.get(node, ()):
                    if color[nb] == WHITE:
                        neighbour = nb
                        break
                    if color[nb] == GRAY and nb in path:
                        cycle_start = path.index(nb)
                        return path[cycle_start:]
                if neighbour is not None:
                    stack.append((neighbour, path + [neighbour]))
                else:
                    color[node] = BLACK
                    stack.pop()
            return None

        for key in list(graph.keys()):
            if color[key] == WHITE:
                cycle = dfs(key)
                if cycle:
                    return cycle
        return None

    def _choose_victim_locked(self, cycle: list[tuple[str, str]]) -> tuple[str, str]:
        """Pick the lowest-cost-score waiter in the cycle as the victim."""
        best = cycle[0]
        best_score = float("inf")
        for key in cycle:
            waiter = self._waiters.get(key)
            score = waiter.request.cost_score() if waiter is not None else 0.0
            # Tie-break on node_id so the choice is deterministic in tests.
            if score < best_score or (score == best_score and key < best):
                best = key
                best_score = score
        return best

    def _evict_holder_locked(self, key: tuple[str, str]) -> None:
        """Drop every lock currently held by ``key``. Used to break deadlocks."""
        handle = self._handles.pop(key, None)
        if handle is None:
            return
        for resource in handle.resources:
            if self._locked.get((handle.run_id, resource)) == handle.node_id:
                self._locked.pop((handle.run_id, resource), None)

    def _reject_waiter_locked(self, key: tuple[str, str], *, reason: str) -> None:
        waiter = self._waiters.pop(key, None)
        if waiter is None:
            return
        waiter.rejected = LockBlocked(reason=reason, contested=waiter.request.resources)
        waiter.event.set()

    def _try_promote_waiters_locked(self) -> None:
        """After a release, hand locks to waiting requests (lowest-score first)."""
        if not self._waiters:
            return
        # Process waiters by ascending score so the most-deserving (highest
        # priority / longest-waiting) get first crack at freed resources.
        ordered = sorted(self._waiters.items(), key=lambda kv: kv[1].request.cost_score())
        for key, waiter in ordered:
            if self._can_acquire_locked(waiter.request):
                handle = self._claim_locked(waiter.request)
                waiter.granted = handle
                self._waiters.pop(key, None)
                waiter.event.set()

    def _sweep_expired_locked(self) -> None:
        now = time.time()
        expired: list[LockHandle] = [h for h in self._handles.values() if h.expires_at <= now]
        for handle in expired:
            logger.warning("lock TTL expired for node %s (run %s)", handle.node_id, handle.run_id)
            self._handles.pop((handle.run_id, handle.node_id), None)
            for resource in handle.resources:
                if self._locked.get((handle.run_id, resource)) == handle.node_id:
                    self._locked.pop((handle.run_id, resource), None)
        if expired:
            self._try_promote_waiters_locked()

    def _start_sweeper(self) -> None:
        def _loop() -> None:
            while not self._stop.wait(timeout=self._sweep_interval):
                try:
                    with self._lock:
                        self._sweep_expired_locked()
                except Exception as exc:
                    logger.warning("lock sweeper failed: %s", exc)

        thread = threading.Thread(target=_loop, name="aitr-lock-sweeper", daemon=True)
        thread.start()
        self._sweeper = thread


__all__ = ["LockManager", "LockHandle", "LockRequest", "LockBlocked"]
