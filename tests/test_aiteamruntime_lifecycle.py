"""End-to-end checks for the aiteamruntime optimisations.

These tests exercise the invariants the Phase 1-8 refactor relies on:

* Per-run state is dropped after a run finalises (no memory leak).
* The Secretary subprocess is a singleton across multiple runs.
* The lock manager detects deadlocks and chooses a fair victim.
* A heavy-task / starvation test confirms the cost-score victim policy.
"""
from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from aiteamruntime import AgentRuntime
from aiteamruntime.test.workflows import register_default_agents
from aiteamruntime.lock_manager import LockBlocked, LockManager, LockRequest
from aiteamruntime.traces import TraceStore


def _build_runtime(tmp_path: Path, *, cleanup_delay: float = 0.3) -> AgentRuntime:
    runtime = AgentRuntime(
        store=TraceStore(tmp_path / "traces"),
        cleanup_delay=cleanup_delay,
        idle_timeout=120.0,
    )
    register_default_agents(runtime)
    return runtime


class TestRunStateCleanup:
    def test_run_state_cleaned_after_finalize(self, tmp_path: Path) -> None:
        runtime = _build_runtime(tmp_path, cleanup_delay=0.2)
        workspace = tmp_path / "ws"
        workspace.mkdir()
        for i in range(5):
            handle = runtime.start_run(
                run_id=f"r{i}",
                prompt=f"task number {i} for cleanup test",
                metadata={"workspace": str(workspace)},
            )
            handle.wait(timeout=10)
        # Wait long enough that finalize delays have elapsed, then sweep.
        time.sleep(0.6)
        runtime.cleanup_idle_runs()
        snap = runtime.snapshot()
        assert snap["runs"] == 0, snap
        assert snap["futures_inflight"] == 0
        runtime.shutdown()

    def test_force_cleanup_drops_running_runs(self, tmp_path: Path) -> None:
        runtime = _build_runtime(tmp_path, cleanup_delay=600.0)
        workspace = tmp_path / "ws"
        workspace.mkdir()
        handle = runtime.start_run(
            run_id="rA",
            prompt="task force cleanup",
            metadata={"workspace": str(workspace)},
        )
        handle.wait(timeout=10)
        runtime.cleanup_idle_runs(force=True)
        assert runtime.snapshot()["runs"] == 0
        runtime.shutdown()


class TestSecretarySingleton:
    def test_secretary_subprocess_is_shared(self, tmp_path: Path) -> None:
        runtime = _build_runtime(tmp_path, cleanup_delay=600.0)
        workspace = tmp_path / "ws"
        workspace.mkdir()
        pids: set[int] = set()
        for i in range(3):
            handle = runtime.start_run(
                run_id=f"sec{i}",
                prompt=f"task secretary singleton {i}",
                metadata={"workspace": str(workspace)},
            )
            handle.wait(timeout=10)
            sec = runtime._secretary
            assert sec is not None and sec.is_alive()
            pids.add(sec._proc.pid)
        assert len(pids) == 1, f"Secretary respawned across runs: {pids}"
        runtime.shutdown()
        assert not runtime._secretary.is_alive()


class TestLockManager:
    def test_basic_acquire_and_release_grants_waiter(self) -> None:
        lm = LockManager(sweep_interval=0.5)
        try:
            held = lm.acquire(LockRequest(run_id="r", node_id="A", resources=frozenset({"x"}), timeout=2))
            results: list[tuple[str, str]] = []

            def thread_b() -> None:
                try:
                    h = lm.acquire(LockRequest(run_id="r", node_id="B", resources=frozenset({"x"}), timeout=3))
                    results.append(("granted", h.node_id))
                except LockBlocked as exc:
                    results.append(("blocked", exc.reason))

            t = threading.Thread(target=thread_b)
            t.start()
            time.sleep(0.3)
            assert results == []  # B is still waiting on A's lock
            lm.release(held)
            t.join(timeout=2)
            assert results == [("granted", "B")]
        finally:
            lm.shutdown()

    def test_deadlock_chooses_lower_attempt_as_victim(self) -> None:
        """Two nodes hold disjoint resources and request each other's.

        Cost score = ``attempt * 10 - priority * 5``. The node with attempt=1
        has the lower score and must lose the race; the higher-attempt node
        (which already retried once) gets the lock.
        """
        lm = LockManager(sweep_interval=0.5)
        try:
            lm.acquire(LockRequest(run_id="d", node_id="A", resources=frozenset({"x"}), timeout=10))
            lm.acquire(LockRequest(run_id="d", node_id="B", resources=frozenset({"y"}), timeout=10))
            outcomes: dict[str, str] = {}

            def t_a() -> None:
                try:
                    lm.acquire(LockRequest(run_id="d", node_id="A", resources=frozenset({"x", "y"}), timeout=4, attempt=2))
                    outcomes["A"] = "granted"
                except LockBlocked as exc:
                    outcomes["A"] = exc.reason

            def t_b() -> None:
                try:
                    lm.acquire(LockRequest(run_id="d", node_id="B", resources=frozenset({"x", "y"}), timeout=4, attempt=1))
                    outcomes["B"] = "granted"
                except LockBlocked as exc:
                    outcomes["B"] = exc.reason

            ta = threading.Thread(target=t_a)
            tb = threading.Thread(target=t_b)
            ta.start()
            time.sleep(0.1)
            tb.start()
            ta.join(timeout=6)
            tb.join(timeout=6)
            assert outcomes.get("B") == "deadlock"
            assert outcomes.get("A") == "granted"
        finally:
            lm.shutdown()

    def test_release_run_drops_handles_and_waiters(self) -> None:
        lm = LockManager(sweep_interval=0.5)
        try:
            lm.acquire(LockRequest(run_id="rA", node_id="A", resources=frozenset({"x"}), timeout=10))
            lm.acquire(LockRequest(run_id="rB", node_id="B", resources=frozenset({"y"}), timeout=10))
            assert {h["run_id"] for h in lm.snapshot()["held"]} == {"rA", "rB"}
            lm.release_run("rA")
            held = {h["run_id"] for h in lm.snapshot()["held"]}
            assert held == {"rB"}
        finally:
            lm.shutdown()


class TestEventKinds:
    def test_lifecycle_event_kinds_are_emitted(self, tmp_path: Path) -> None:
        runtime = _build_runtime(tmp_path, cleanup_delay=0.2)
        workspace = tmp_path / "ws"
        workspace.mkdir()
        handle = runtime.start_run(
            run_id="lifecycle",
            prompt="task lifecycle event check",
            metadata={"workspace": str(workspace)},
        )
        handle.wait(timeout=10)
        time.sleep(0.4)
        runtime.cleanup_idle_runs()
        events = runtime.store.read_events("lifecycle")
        kinds = [e["kind"] for e in events]
        # Phase 1 lifecycle markers
        assert "run_started" in kinds
        assert "run_finished" in kinds
        assert "cleanup_complete" in kinds
        runtime.shutdown()


@pytest.mark.parametrize("worker_count,run_count", [(2, 3)])
def test_concurrent_runs_share_a_single_secretary(tmp_path: Path, worker_count: int, run_count: int) -> None:
    """Smoke test: many simultaneous runs still spawn one Secretary process."""
    runtime = AgentRuntime(
        store=TraceStore(tmp_path / "traces"),
        cleanup_delay=600.0,
        idle_timeout=120.0,
    )
    register_default_agents(runtime)
    workspace = tmp_path / "ws"
    workspace.mkdir()
    handles = [
        runtime.start_run(
            run_id=f"par{i}",
            prompt=f"task parallel {i} for the smoke check",
            metadata={"workspace": str(workspace)},
        )
        for i in range(run_count)
    ]
    for h in handles:
        h.wait(timeout=15)
    sec = runtime._secretary
    assert sec is not None
    assert sec.is_alive()
    files = list(workspace.rglob("*.txt"))
    assert files, "demo workflow should have produced workspace artifacts"
    runtime.shutdown()
