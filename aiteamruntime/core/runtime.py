from __future__ import annotations

from collections import deque
from dataclasses import replace
from concurrent.futures import Future
import logging
import threading
import time
import uuid
from typing import Any

from .bus import EventBus
from .context import AgentContext, RunHandle
from .contracts import AgentContract, SchemaValidator
from .events import AgentEvent
from .governor import GovernorLimits, GovernorState
from ..resources.locks import LockManager
from .overseer import OverseerPolicy, OverseerState
from .references import ReferenceStore
from ..resources.workspace import ResourceManager, normalize_file_path
from .scheduler import AgentScheduler
from .state import AgentSpec, RunState, WorkItem
from ..tracing.store import TraceStore

logger = logging.getLogger(__name__)

# Events that signal a run is naturally complete and should be cleaned up.
_TERMINAL_KINDS = frozenset({"finalized", "run_finished", "run_aborted"})
_GOVERNOR_EXEMPT_KINDS = frozenset(
    {"quota_exceeded", "abort", "run_aborted", "run_finished", "cleanup_complete", "error"}
)
_CONTRACT_INTERNAL_KINDS = frozenset(
    {
        "schema_error",
        "schema_repair_requested",
        "schema_repaired",
        "quota_exceeded",
        "abort",
        "abort_task",
        "overseer_action",
        "blocked",
        "error",
        "hydrated",
    }
)
_OVERSEER_FAILURE_KINDS = frozenset({"worker_failed", "error", "timeout"})

class AgentRuntime:
    """Standalone event-driven runtime.

    The runtime is deliberately not wired into the production LangGraph flow
    yet. It can run demo or experimental agents, persist trace JSONL, and power
    the web viewer while the trigger model matures.
    """

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        store: TraceStore | None = None,
        scheduler: AgentScheduler | None = None,
        resources: ResourceManager | None = None,
        max_events_per_run: int = 1000,
        max_trigger_depth: int = 20,
        cleanup_delay: float = 60.0,
        idle_timeout: float = 300.0,
        max_inflight_futures: int = 1024,
        governor_defaults: GovernorLimits | dict[str, Any] | None = None,
        reference_store: ReferenceStore | None = None,
        contract_repair_agent_id: str = "Secretary",
        enable_overseer: bool = True,
        overseer_policy: OverseerPolicy | None = None,
    ) -> None:
        self.bus = bus or EventBus()
        self.store = store or TraceStore()
        self.scheduler = scheduler or AgentScheduler(self.bus)
        self.resources = resources or ResourceManager()
        self.locks = LockManager()
        self.max_events_per_run = max(1, int(max_events_per_run))
        if governor_defaults is None:
            self.governor_defaults = GovernorLimits(max_events=self.max_events_per_run)
        elif isinstance(governor_defaults, dict):
            self.governor_defaults = GovernorLimits(**governor_defaults)
        else:
            self.governor_defaults = governor_defaults
        self.references = reference_store or ReferenceStore(self.store.root)
        self.contract_repair_agent_id = str(contract_repair_agent_id or "Secretary")
        self.enable_overseer = bool(enable_overseer)
        self._overseer = OverseerState(overseer_policy or OverseerPolicy())
        self._validator = SchemaValidator()
        self.max_trigger_depth = max(1, int(max_trigger_depth))
        self.cleanup_delay = max(0.0, float(cleanup_delay))
        self.idle_timeout = max(0.0, float(idle_timeout))
        self._agents: list[AgentSpec] = []
        self._agents_by_kind: dict[str, list[AgentSpec]] = {}
        self._agents_catch_all: list[AgentSpec] = []
        self._futures: deque[tuple[str, Future]] = deque(maxlen=max(64, int(max_inflight_futures)))
        self._secretary: Any = None  # lazy SecretaryProcess
        # Bounded LRU of run_ids that completed cleanup. Late events for these
        # runs are dropped instead of resurrecting fresh RunState entries.
        self._recently_cleaned: deque[str] = deque(maxlen=512)
        self._cleaned_set: set[str] = set()
        self._lock = threading.RLock()
        self._runs: dict[str, RunState] = {}
        self._shutdown_event = threading.Event()
        self._watchdog: threading.Thread | None = None
        self._start_watchdog()

    def register(self, spec: AgentSpec) -> AgentSpec:
        with self._lock:
            self._agents.append(spec)
            if spec.triggers_kinds:
                for kind in spec.triggers_kinds:
                    self._agents_by_kind.setdefault(kind, []).append(spec)
            else:
                self._agents_catch_all.append(spec)
        return spec

    def _candidate_specs(self, event: AgentEvent) -> list[AgentSpec]:
        """Return specs that *might* match the event, using the kind index."""
        with self._lock:
            indexed = self._agents_by_kind.get(event.kind, ())
            return list(indexed) + list(self._agents_catch_all)

    def _get_or_create_run(self, run_id: str) -> RunState | None:
        """Return existing RunState or create a fresh one. Thread-safe.

        Returns ``None`` for run_ids that have already been cleaned up — late
        events from agents that haven't noticed the run is over should be
        dropped, not resurrect a fresh state entry.
        """
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                return run
            if run_id in self._cleaned_set:
                return None
            run = RunState(run_id=run_id)
            run.governor = GovernorState(limits=replace(self.governor_defaults), started_at=run.started_at)
            self._runs[run_id] = run
            return run

    def start_run(
        self,
        *,
        run_id: str | None = None,
        prompt: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> RunHandle:
        rid = run_id or f"run-{uuid.uuid4().hex[:12]}"
        metadata = dict(metadata or {})
        # If the caller reused a previously-cleaned run_id, allow a fresh start
        # by removing it from the cleaned LRU.
        with self._lock:
            self._cleaned_set.discard(rid)
        run = self._get_or_create_run(rid)
        if run is None:
            # Should not happen because we just discarded from cleaned_set, but
            # be defensive in case of races.
            run = self._get_or_create_run(rid)
            assert run is not None
        workspace = str(metadata.get("workspace") or "")
        if workspace:
            decision = self.resources.set_workspace(rid, workspace)
            if not decision.allowed:
                self.store.start_run(rid, {"prompt": prompt, **metadata})
                with self._lock:
                    run.state = "aborted"
                self._publish(
                    AgentEvent(
                        run_id=rid,
                        agent_id="runtime",
                        kind="error",
                        status="error",
                        payload={"reason": decision.reason, "workspace": workspace},
                        stage="setup",
                        role_state="error",
                    ),
                    dispatch=False,
                )
                self._schedule_finalize(rid, kind="run_aborted")
                return RunHandle(rid, self)
        self.store.start_run(rid, {"prompt": prompt, **metadata})
        # Lifecycle event: emitted before classifying so subscribers see the canonical
        # boundary of a run independent of agent activity.
        self.emit(
            rid,
            "runtime",
            "run_started",
            {"prompt": prompt, "metadata": metadata, "workspace": self.resources.workspace_for(rid)},
            stage="lifecycle",
            role_state="running",
        )
        self.emit(
            rid,
            "runtime",
            "classifying",
            {"prompt": prompt, "metadata": metadata, "workspace": self.resources.workspace_for(rid)},
            stage="classify",
            role_state="running",
        )
        return RunHandle(rid, self)

    def resume_run(self, run_id: str, *, metadata: dict[str, Any] | None = None) -> bool:
        """Rehydrate in-memory state for a persisted run without starting it over."""
        metadata = dict(metadata or {})
        with self._lock:
            self._cleaned_set.discard(run_id)
            try:
                self._recently_cleaned.remove(run_id)
            except ValueError:
                pass
        run = self._get_or_create_run(run_id)
        if run is None:
            return False
        workspace = str(metadata.get("workspace") or "")
        if workspace:
            decision = self.resources.set_workspace(run_id, workspace)
            if not decision.allowed:
                self._publish(
                    AgentEvent(
                        run_id=run_id,
                        agent_id="runtime",
                        kind="error",
                        status="error",
                        payload={"reason": decision.reason, "workspace": workspace},
                        stage="setup",
                        role_state="error",
                    ),
                    dispatch=False,
                )
                return False
        with self._lock:
            run.state = "running"
        return True

    def emit(
        self,
        run_id: str,
        agent_id: str,
        kind: str,
        payload: dict[str, Any] | None = None,
        *,
        status: str = "ok",
        parent_event: AgentEvent | None = None,
        stage: str = "",
        work_item_id: str = "",
        resource_key: str = "",
        duration_ms: int = 0,
        role_state: str = "",
        assignment: dict[str, Any] | None = None,
        retry_of: str = "",
    ) -> AgentEvent:
        parent_event_id = parent_event.event_id if parent_event else ""
        correlation_id = parent_event.correlation_id if parent_event else ""
        depth = (parent_event.depth + 1) if parent_event else 0
        if self.is_aborted(run_id) and kind != "abort":
            return self._publish(
                AgentEvent(
                    run_id=run_id,
                    agent_id="runtime",
                    kind="blocked",
                    payload={"reason": "run aborted", "blocked_kind": kind, "blocked_agent_id": agent_id},
                    status="blocked",
                    parent_event_id=parent_event_id,
                    correlation_id=correlation_id,
                    depth=depth,
                    stage=stage,
                    work_item_id=work_item_id,
                    resource_key=resource_key,
                    duration_ms=duration_ms,
                    role_state=role_state,
                    assignment=dict(assignment or {}),
                    retry_of=retry_of,
                ),
                dispatch=False,
            )
        if depth > self.max_trigger_depth:
            self.request_abort(run_id, f"max trigger depth exceeded: {depth}")
            return self._publish(
                AgentEvent(
                    run_id=run_id,
                    agent_id="runtime",
                    kind="error",
                    payload={"reason": "max trigger depth exceeded", "depth": depth},
                    status="error",
                    parent_event_id=parent_event_id,
                    correlation_id=correlation_id,
                    depth=depth,
                    stage=stage,
                    work_item_id=work_item_id,
                    role_state="error",
                ),
                dispatch=False,
            )

        blocked = self._resource_preflight(run_id, agent_id, kind, payload or {})
        if blocked is not None:
            blocked = AgentEvent(
                run_id=blocked.run_id,
                agent_id=blocked.agent_id,
                kind=blocked.kind,
                payload=blocked.payload,
                ts=blocked.ts,
                status=blocked.status,
                event_id=blocked.event_id,
                parent_event_id=parent_event_id,
                correlation_id=correlation_id or blocked.correlation_id,
                depth=depth,
                dedupe_key=blocked.dedupe_key,
                stage=stage or blocked.stage,
                work_item_id=work_item_id or blocked.work_item_id,
                resource_key=resource_key or blocked.resource_key,
                duration_ms=duration_ms or blocked.duration_ms,
                role_state=role_state or blocked.role_state,
                assignment=dict(assignment or blocked.assignment or {}),
                retry_of=retry_of or blocked.retry_of,
            )
            return self._publish(blocked, dispatch=True)

        payload = payload or {}
        repair_event = self._validate_output_contract(
            run_id,
            agent_id,
            kind,
            payload,
            parent_event=parent_event,
            status=status,
            stage=stage,
            work_item_id=work_item_id,
        )
        if repair_event is not None:
            return repair_event
        stage = stage or str(payload.get("stage") or "")
        work_item_id = work_item_id or str(payload.get("work_item_id") or payload.get("id") or "")
        resource_key = resource_key or str(payload.get("resource_key") or payload.get("path") or payload.get("file") or "")
        if assignment is None and isinstance(payload.get("assignment"), dict):
            assignment = dict(payload.get("assignment") or {})
        event = AgentEvent(
            run_id=run_id,
            agent_id=agent_id,
            kind=kind,
            payload=payload,
            status=status,
            parent_event_id=parent_event_id,
            correlation_id=correlation_id,
            depth=depth,
            dedupe_key=self._dedupe_key(run_id, agent_id, kind, payload),
            stage=stage,
            work_item_id=work_item_id,
            resource_key=resource_key,
            duration_ms=duration_ms,
            role_state=role_state,
            assignment=dict(assignment or {}),
            retry_of=retry_of,
        )
        self._track_event(event)
        if kind == "done":
            self.resources.release_agent(run_id, agent_id)
            self._release_worker(run_id, agent_id)
        if kind in {"setup_done", "terminal_result"}:
            command = str((payload or {}).get("command") or "")
            cwd = str((payload or {}).get("cwd") or ".")
            self.resources.complete_terminal(run_id, command, cwd, payload or {})
        return self._publish(event, dispatch=True)

    def _contract_for(self, agent_id: str) -> AgentContract | None:
        with self._lock:
            for spec in self._agents:
                if spec.agent_id == agent_id:
                    return spec.contract
        return None

    def _validate_output_contract(
        self,
        run_id: str,
        agent_id: str,
        kind: str,
        payload: dict[str, Any],
        *,
        parent_event: AgentEvent | None,
        status: str,
        stage: str,
        work_item_id: str,
    ) -> AgentEvent | None:
        if kind in _CONTRACT_INTERNAL_KINDS:
            return None
        contract = self._contract_for(agent_id)
        if contract is None or not contract.should_validate_output(kind):
            return None
        result = self._validator.validate(payload, contract.output_schema)
        if result.ok:
            return None
        parent_event_id = parent_event.event_id if parent_event else ""
        correlation_id = parent_event.correlation_id if parent_event else ""
        depth = (parent_event.depth + 1) if parent_event else 0
        repair_attempt_count = int(payload.get("repair_attempt_count") or 0)
        body = {
            "source_agent_id": agent_id,
            "source_kind": kind,
            "source_status": status,
            "errors": list(result.errors),
            "repair_attempt_count": repair_attempt_count,
            "schema_version": contract.version,
        }
        if agent_id == self.contract_repair_agent_id or repair_attempt_count >= contract.max_secretary_repair_attempts:
            return self._publish(
                AgentEvent(
                    run_id=run_id,
                    agent_id="runtime",
                    kind="schema_error",
                    status="error",
                    payload=body,
                    parent_event_id=parent_event_id,
                    correlation_id=correlation_id,
                    depth=depth,
                    stage=stage,
                    work_item_id=work_item_id,
                    role_state="error",
                ),
                dispatch=True,
            )
        body["repair_attempt_count"] = repair_attempt_count + 1
        return self._publish(
            AgentEvent(
                run_id=run_id,
                agent_id="runtime",
                kind="schema_repair_requested",
                status="waiting",
                payload=body,
                parent_event_id=parent_event_id,
                correlation_id=correlation_id,
                depth=depth,
                stage=stage,
                work_item_id=work_item_id,
                role_state="waiting",
            ),
            dispatch=True,
        )

    def _track_event(self, event: AgentEvent) -> None:
        run = self._get_or_create_run(event.run_id)
        if run is None:
            return  # late event for an already-cleaned run
        if event.kind in {"assigned", "reassigned"}:
            item_payload = dict(event.assignment or event.payload.get("work_item") or event.payload)
            item = WorkItem.from_payload(item_payload)
            item.status = "assigned"
            item.assigned_worker = str(item_payload.get("assigned_worker") or event.payload.get("assigned_worker") or event.agent_id)
            item.attempt = int(item_payload.get("attempt") or item.attempt or (1 if event.kind == "assigned" else 2))
            with self._lock:
                run.work_items[item.id] = item
                run.worker_busy[item.assigned_worker] = item.id
        elif event.kind == "done" and event.work_item_id:
            with self._lock:
                item = run.work_items.get(event.work_item_id)
            if item is not None:
                item.status = "done"
        elif event.kind == "worker_failed" and event.work_item_id:
            with self._lock:
                item = run.work_items.get(event.work_item_id)
                if item is not None:
                    item.status = "failed"
                    run.worker_busy.pop(item.assigned_worker, None)
        elif event.kind == "abort_task" and event.work_item_id:
            with self._lock:
                item = run.work_items.get(event.work_item_id)
                if item is not None:
                    item.status = "aborted"
                    run.worker_busy.pop(item.assigned_worker, None)
                    self.resources.release_agent(event.run_id, item.assigned_worker)
        elif event.kind == "validated":
            with self._lock:
                for item in run.work_items.values():
                    if item.status == "assigned":
                        item.status = "done"

    def _release_worker(self, run_id: str, agent_id: str) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                run.worker_busy.pop(agent_id, None)

    def assignments_snapshot(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return []
            return [item.to_dict() for item in run.work_items.values()]

    def idle_workers(self, run_id: str, workers: list[str]) -> list[str]:
        with self._lock:
            run = self._runs.get(run_id)
            busy = set(run.worker_busy.keys()) if run is not None else set()
        return [worker for worker in workers if worker not in busy]

    def _publish(self, event: AgentEvent, *, dispatch: bool) -> AgentEvent:
        run = self._get_or_create_run(event.run_id)
        if run is None:
            # Late-arriving event for a run that was already cleaned up — drop
            # silently so we don't resurrect state or write to a stale trace.
            return event
        post_quota_reason = ""
        with self._lock:
            run.event_count += 1
            now = time.time()
            if run.governor is not None and event.kind not in _GOVERNOR_EXEMPT_KINDS:
                reason = run.governor.check_pre_publish(event_count=run.event_count, now=now)
                if reason:
                    run.governor.freeze(reason)
                    event = AgentEvent(
                        run_id=event.run_id,
                        agent_id="runtime",
                        kind="quota_exceeded",
                        status="aborted",
                        payload={"reason": reason, "blocked_kind": event.kind, "blocked_agent_id": event.agent_id},
                        parent_event_id=event.parent_event_id,
                        correlation_id=event.correlation_id,
                        depth=event.depth,
                        stage=event.stage or "runtime",
                        work_item_id=event.work_item_id,
                        role_state="aborted",
                    )
            run.seq += 1
            seq = run.seq
            run.last_event_at = now
            event = AgentEvent(
                run_id=event.run_id,
                agent_id=event.agent_id,
                kind=event.kind,
                payload=event.payload,
                ts=event.ts,
                status=event.status,
                event_id=event.event_id,
                parent_event_id=event.parent_event_id,
                correlation_id=event.correlation_id,
                sequence=seq,
                attempt=event.attempt,
                depth=event.depth,
                dedupe_key=event.dedupe_key,
                stage=event.stage,
                work_item_id=event.work_item_id,
                resource_key=event.resource_key,
                duration_ms=event.duration_ms,
                role_state=event.role_state,
                assignment=dict(event.assignment or {}),
                retry_of=event.retry_of,
            )
            if run.governor is not None and event.kind not in _GOVERNOR_EXEMPT_KINDS:
                post_quota_reason = run.governor.observe_o1(event)
                if post_quota_reason:
                    run.governor.freeze(post_quota_reason)
        self.store.append(event)
        self.bus.publish(event)
        if dispatch:
            self._dispatch(event)
        if event.kind == "quota_exceeded" and not self.is_aborted(event.run_id):
            self.request_abort(event.run_id, str((event.payload or {}).get("reason") or "quota exceeded"))
        if post_quota_reason:
            self._publish(
                AgentEvent(
                    run_id=event.run_id,
                    agent_id="runtime",
                    kind="quota_exceeded",
                    status="aborted",
                    payload={"reason": post_quota_reason},
                    parent_event_id=event.event_id,
                    correlation_id=event.correlation_id,
                    depth=event.depth + 1,
                    stage="runtime",
                    role_state="aborted",
                ),
                dispatch=False,
            )
            self.request_abort(event.run_id, post_quota_reason)
        if self.enable_overseer and event.kind in _OVERSEER_FAILURE_KINDS and event.agent_id != "Overseer":
            self._overseer_observe(event)
        # Auto-finalize when terminal event arrives. Done outside dispatch so
        # subscribers see the lifecycle event before cleanup happens.
        if event.kind == "finalized" and event.agent_id != "runtime":
            self._schedule_finalize(event.run_id, kind="run_finished")
        elif event.kind in _TERMINAL_KINDS and event.agent_id == "runtime":
            self._schedule_finalize(event.run_id, kind=event.kind, immediate=event.kind == "run_aborted")
        return event

    def _overseer_observe(self, event: AgentEvent) -> None:
        if event.kind == "error" and not event.work_item_id and not (event.payload or {}).get("work_item_id"):
            return
        action, count = self._overseer.record_failure(event)
        work_item_id = event.work_item_id or str((event.payload or {}).get("work_item_id") or "")
        self._publish(
            AgentEvent(
                run_id=event.run_id,
                agent_id="Overseer",
                kind="overseer_action",
                payload={
                    "action": action,
                    "failure_count": count,
                    "source_event_id": event.event_id,
                    "work_item_id": work_item_id,
                },
                parent_event_id=event.event_id,
                correlation_id=event.correlation_id,
                depth=event.depth + 1,
                stage=event.stage or "overseer",
                work_item_id=work_item_id,
            ),
            dispatch=False,
        )
        if not work_item_id:
            return
        if action == "abort_task":
            self.emit(
                event.run_id,
                "Overseer",
                "abort_task",
                {"work_item_id": work_item_id, "reason": "failure threshold exceeded"},
                status="aborted",
                parent_event=event,
                stage=event.stage or "overseer",
                work_item_id=work_item_id,
                role_state="aborted",
            )
            return
        replacement = self._select_replacement_worker(event.run_id, work_item_id)
        if not replacement:
            return
        with self._lock:
            run = self._runs.get(event.run_id)
            item = run.work_items.get(work_item_id) if run is not None else None
            if item is None:
                return
            item.assigned_worker = replacement
            item.status = "assigned"
            item.attempt += 1
            assignment = item.to_dict()
            run.worker_busy[replacement] = work_item_id
        assignment["escalated"] = action == "escalate"
        self.emit(
            event.run_id,
            "Overseer",
            "reassigned",
            {"work_item": assignment, "assigned_worker": replacement, "reason": action},
            parent_event=event,
            stage=event.stage or "overseer",
            work_item_id=work_item_id,
            assignment=assignment,
        )

    def _select_replacement_worker(self, run_id: str, work_item_id: str) -> str:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return ""
            item = run.work_items.get(work_item_id)
            known = sorted({wi.assigned_worker for wi in run.work_items.values() if wi.assigned_worker})
            busy = set(run.worker_busy)
            current = item.assigned_worker if item is not None else ""
        for worker in known:
            if worker != current and worker not in busy:
                return worker
        return current if current and current not in busy else ""

    def _resource_preflight(
        self,
        run_id: str,
        agent_id: str,
        kind: str,
        payload: dict[str, Any],
    ) -> AgentEvent | None:
        if kind in {"writing", "file_update", "file_create"}:
            path = str(payload.get("path") or payload.get("file") or "")
            work_item_id = str(payload.get("work_item_id") or "")
            if path and work_item_id:
                with self._lock:
                    run = self._runs.get(run_id)
                    item = run.work_items.get(work_item_id) if run is not None else None
                    allowed_paths = list(item.allowed_paths) if item is not None else []
                if allowed_paths:
                    key = normalize_file_path(path)
                    allowed = {normalize_file_path(item_path) for item_path in allowed_paths}
                    if key not in allowed:
                        return AgentEvent(
                            run_id=run_id,
                            agent_id=agent_id,
                            kind="blocked",
                            status="blocked",
                            payload={
                                "resource_type": "file",
                                "resource_key": key,
                                "reason": "path is outside work item allowed_paths",
                                "blocked_kind": kind,
                                "allowed_paths": sorted(allowed),
                                "work_item_id": work_item_id,
                            },
                            stage=str(payload.get("stage") or ""),
                            work_item_id=work_item_id,
                            resource_key=key,
                            role_state="blocked",
                        )
            decision = self.resources.acquire_file(run_id, agent_id, path)
            if not decision.allowed:
                return AgentEvent(
                    run_id=run_id,
                    agent_id=agent_id,
                    kind="blocked",
                    status="blocked",
                    payload={
                        "resource_type": decision.resource_type,
                        "resource_key": decision.key,
                        "owner_agent_id": decision.owner_agent_id,
                        "reason": decision.reason,
                        "blocked_kind": kind,
                    },
                    stage=str(payload.get("stage") or ""),
                    work_item_id=str(payload.get("work_item_id") or ""),
                    resource_key=decision.key,
                    role_state="blocked",
                )
        if kind in {"setup_requested", "terminal_requested"}:
            command = str(payload.get("command") or "")
            cwd = str(payload.get("cwd") or ".")
            decision = self.resources.request_terminal(run_id, agent_id, command, cwd)
            if not decision.allowed:
                body = {
                    "resource_type": decision.resource_type,
                    "resource_key": decision.key,
                    "owner_agent_id": decision.owner_agent_id,
                    "reason": decision.reason,
                    "blocked_kind": kind,
                    "command": command,
                    "cwd": cwd,
                }
                if decision.reused_payload is not None:
                    body["reused_result"] = decision.reused_payload
                return AgentEvent(
                    run_id=run_id,
                    agent_id=agent_id,
                    kind="blocked",
                    status="reused" if decision.reused_payload is not None else "blocked",
                    payload=body,
                    stage=str(payload.get("stage") or ""),
                    work_item_id=str(payload.get("work_item_id") or ""),
                    resource_key=decision.key,
                    role_state="blocked",
                )
        return None

    def _dedupe_key(self, run_id: str, agent_id: str, kind: str, payload: dict[str, Any]) -> str:
        if kind in {"setup_requested", "terminal_requested"}:
            command = str(payload.get("command") or "")
            cwd = str(payload.get("cwd") or ".")
            return f"{run_id}:{agent_id}:terminal:{cwd}:{command}"
        if kind in {"writing", "file_update", "file_create"}:
            return f"{run_id}:{agent_id}:file:{payload.get('path') or payload.get('file') or ''}"
        return f"{run_id}:{agent_id}:{kind}"

    def _dispatch(self, event: AgentEvent) -> None:
        if self.is_aborted(event.run_id):
            return
        run = self._get_or_create_run(event.run_id)
        if run is None:
            return
        for spec in self._candidate_specs(event):
            if spec.agent_id == event.agent_id:
                continue
            try:
                matched = spec.matches(event)
            except Exception as exc:
                self.emit(
                    event.run_id,
                    spec.agent_id,
                    "error",
                    {"type": type(exc).__name__, "message": str(exc), "phase": "trigger"},
                    status="error",
                )
                continue
            if not matched:
                continue
            schedule_key = f"{spec.agent_id}:{event.event_id}"
            with self._lock:
                if schedule_key in run.scheduled_events:
                    continue
                # Backpressure: if scheduler is overloaded, signal and drop this
                # dispatch instead of letting the executor queue grow forever.
                if not self.scheduler.has_capacity():
                    self._emit_pool_full(event, spec)
                    continue
                run.scheduled_events.add(schedule_key)

            def _run_agent(spec: AgentSpec = spec, event: AgentEvent = event) -> object:
                hydrated_event = self._hydrate_for_agent(event, spec)
                if hydrated_event is None:
                    return None
                if spec.contract is not None and spec.contract.input_schema:
                    result = self._validator.validate(hydrated_event.payload, spec.contract.input_schema)
                    if not result.ok:
                        self.emit(
                            event.run_id,
                            "runtime",
                            "schema_error",
                            {
                                "target_agent_id": spec.agent_id,
                                "phase": "input",
                                "errors": list(result.errors),
                                "schema_version": spec.contract.version,
                            },
                            status="error",
                            parent_event=event,
                            stage=event.stage,
                            work_item_id=event.work_item_id,
                            role_state="error",
                        )
                        return None
                ctx = AgentContext(self, hydrated_event.run_id, spec.agent_id, hydrated_event)
                try:
                    return spec.handler(ctx, hydrated_event)
                except Exception as exc:
                    self.emit(
                        event.run_id,
                        spec.agent_id,
                        "error",
                        {"type": type(exc).__name__, "message": str(exc), "phase": "handler"},
                        status="error",
                        parent_event=event,
                    )
                    raise

            future = self.scheduler.submit(event.run_id, spec.agent_id, _run_agent)
            entry = (event.run_id, future)
            self._futures.append(entry)
            # Remove the future from the deque as soon as it completes so
            # in-flight tracking stays bounded by actual concurrency, not history.
            future.add_done_callback(lambda _f, e=entry: self._discard_future(e))

    def _hydrate_for_agent(self, event: AgentEvent, spec: AgentSpec) -> AgentEvent | None:
        refs = (event.payload or {}).get("refs") or []
        if not refs:
            return event
        hydrated: dict[str, dict[str, Any]] = {}
        ref_ids: list[str] = []
        try:
            for ref in refs:
                ref_id = str(ref.get("id") if isinstance(ref, dict) else ref)
                if not ref_id:
                    continue
                hydrated[ref_id] = self.references.hydrate(
                    event.run_id,
                    ref_id,
                    workspace=self.resources.workspace_for(event.run_id),
                )
                ref_ids.append(ref_id)
        except Exception as exc:
            self.emit(
                event.run_id,
                "runtime",
                "blocked",
                {"reason": str(exc), "target_agent_id": spec.agent_id, "refs": ref_ids, "phase": "hydrate"},
                status="blocked",
                parent_event=event,
                stage=event.stage,
                work_item_id=event.work_item_id,
                role_state="blocked",
            )
            return None
        self.emit(
            event.run_id,
            "runtime",
            "hydrated",
            {"target_agent_id": spec.agent_id, "refs": ref_ids},
            parent_event=event,
            stage=event.stage,
            work_item_id=event.work_item_id,
            role_state="done",
        )
        payload = dict(event.payload or {})
        payload["_hydrated"] = hydrated
        return replace(event, payload=payload)

    def _emit_pool_full(self, event: AgentEvent, spec: AgentSpec) -> None:
        """Signal scheduler overload. Coalesced — emitted at most once per second per run."""
        run = self._get_or_create_run(event.run_id)
        if run is None:
            return
        now = time.time()
        if now - run.pool_full_last < 1.0:
            return
        run.pool_full_last = now
        self._publish(
            AgentEvent(
                run_id=event.run_id,
                agent_id="runtime",
                kind="worker_pool_full",
                status="blocked",
                payload={
                    "skipped_agent_id": spec.agent_id,
                    "trigger_event_id": event.event_id,
                    "trigger_kind": event.kind,
                    "pending": self.scheduler.pending_count(),
                    "max_pending": self.scheduler.max_pending,
                },
                stage="runtime",
            ),
            dispatch=False,
        )

    def _discard_future(self, entry: tuple[str, Future]) -> None:
        try:
            self._futures.remove(entry)
        except ValueError:
            pass  # already evicted by deque maxlen

    def request_abort(self, run_id: str, reason: str = "aborted") -> None:
        run = self._get_or_create_run(run_id)
        if run is None:
            return  # already cleaned up
        with self._lock:
            run.state = "aborted"
        self.scheduler.request_abort(run_id, reason)
        self._publish(
            AgentEvent(
                run_id=run_id,
                agent_id="runtime",
                kind="abort",
                status="aborted",
                payload={"reason": reason},
            ),
            dispatch=False,
        )
        self._schedule_finalize(run_id, kind="run_aborted", immediate=True)

    def is_aborted(self, run_id: str) -> bool:
        if self.scheduler.is_aborted(run_id):
            return True
        with self._lock:
            run = self._runs.get(run_id)
            return run is not None and run.state == "aborted"

    def run_state(self, run_id: str) -> str:
        with self._lock:
            run = self._runs.get(run_id)
            if run is not None:
                return run.state
            if run_id in self._cleaned_set:
                return "cleaned"
            stored = next((item for item in self.store.list_runs() if item.get("run_id") == run_id), None)
            if stored is not None:
                return str(stored.get("status") or "created")
            return "created"

    def resource_snapshot(self, run_id: str) -> dict[str, Any]:
        return self.resources.snapshot(run_id)

    def governor_snapshot(self, run_id: str) -> dict[str, Any]:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.governor is None:
                return {}
            return run.governor.snapshot()

    def refs_snapshot(self, run_id: str) -> list[dict[str, Any]]:
        return self.references.metadata(run_id)

    def contracts_snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            specs = list(self._agents)
        out = []
        for spec in specs:
            if spec.contract is None:
                continue
            out.append(
                {
                    "agent_id": spec.agent_id,
                    "version": spec.contract.version,
                    "output_kinds": sorted(spec.contract.output_kinds),
                    "has_input_schema": bool(spec.contract.input_schema),
                    "has_output_schema": bool(spec.contract.output_schema),
                }
            )
        return out

    def wait(self, *, run_id: str | None = None, timeout: float | None = None) -> None:
        deadline = None if timeout is None else time.monotonic() + timeout
        seen: set[int] = set()
        while True:
            pending = [
                future
                for rid, future in list(self._futures)
                if (run_id is None or rid == run_id) and id(future) not in seen
            ]
            if not pending:
                return
            for future in pending:
                remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
                try:
                    future.result(timeout=remaining)
                except Exception:
                    # Errors are already emitted as events by the agent wrapper;
                    # wait() should not raise on individual handler failures.
                    pass
                seen.add(id(future))
            if deadline is not None and time.monotonic() >= deadline:
                return

    # ── Lifecycle / cleanup ───────────────────────────────────────────────

    def _schedule_finalize(self, run_id: str, *, kind: str, immediate: bool = False) -> None:
        """Mark a run as finished/aborted and schedule cleanup.

        ``immediate`` skips the cleanup_delay grace period — used for aborts.
        """
        needs_emit = False
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return
            if run.state == "running":
                run.state = "finished" if kind == "run_finished" else "aborted"
            # Idempotent — first caller wins
            if run.finalize_at == 0.0:
                delay = 0.0 if immediate else self.cleanup_delay
                run.finalize_at = time.time() + delay
                # Emit lifecycle event (skipped if we're already mid-finalize)
                needs_emit = kind in {"run_finished", "run_aborted"}
        if needs_emit:
            self._publish(
                AgentEvent(
                    run_id=run_id,
                    agent_id="runtime",
                    kind=kind,
                    status="aborted" if kind == "run_aborted" else "done",
                    payload={"finalize_in": self.cleanup_delay if not immediate else 0.0},
                    stage="lifecycle",
                ),
                dispatch=False,
            )

    def cleanup_run(self, run_id: str) -> bool:
        """Drop all per-run state. Returns True if a run was cleaned up."""
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return False
            # Mark cleaned so re-create paths can detect double-cleanup.
            run.state = "cleaned"
            event_count = run.event_count
            duration = time.time() - run.started_at
        # Emit cleanup_complete BEFORE popping so seq is contiguous and SSE
        # clients see the lifecycle marker without a fresh RunState appearing.
        self._publish(
            AgentEvent(
                run_id=run_id,
                agent_id="runtime",
                kind="cleanup_complete",
                status="done",
                payload={"events": event_count, "duration_s": duration},
                stage="lifecycle",
            ),
            dispatch=False,
        )
        with self._lock:
            self._runs.pop(run_id, None)
            # Track recently cleaned run_ids so late events don't resurrect state.
            # When the LRU is full, evict the oldest entry from both structures.
            cleaned = self._recently_cleaned
            if cleaned.maxlen is not None and len(cleaned) >= cleaned.maxlen:
                self._cleaned_set.discard(cleaned[0])
            cleaned.append(run_id)
            self._cleaned_set.add(run_id)
        # Clean external state holders.
        self.resources.release_run(run_id)
        self.locks.release_run(run_id)
        # Drop scheduler abort flag so the slot can be reused if run_id is reused.
        self.scheduler.clear_abort(run_id)
        return True

    def cleanup_idle_runs(self, *, force: bool = False) -> int:
        """Sweep runs whose finalize_at has elapsed (or all if ``force``)."""
        now = time.time()
        to_clean: list[str] = []
        with self._lock:
            for rid, run in list(self._runs.items()):
                if force:
                    to_clean.append(rid)
                elif run.finalize_at and now >= run.finalize_at:
                    to_clean.append(rid)
                elif self.idle_timeout > 0 and (now - run.last_event_at) > self.idle_timeout and run.state == "running":
                    # Watchdog: idle too long, mark aborted
                    run.state = "aborted"
                    run.finalize_at = now  # trigger cleanup next sweep
        for rid in to_clean:
            self.cleanup_run(rid)
        return len(to_clean)

    def _start_watchdog(self) -> None:
        """Start a single shared daemon thread that sweeps idle runs every 5s."""
        if self.cleanup_delay <= 0 and self.idle_timeout <= 0:
            return  # cleanup disabled

        def _loop() -> None:
            while not self._shutdown_event.wait(timeout=5.0):
                try:
                    self.cleanup_idle_runs()
                except Exception as exc:
                    logger.warning("watchdog sweep failed: %s", exc)

        thread = threading.Thread(target=_loop, name="aitr-watchdog", daemon=True)
        thread.start()
        self._watchdog = thread

    def snapshot(self) -> dict[str, Any]:
        """Debug helper: returns counts of in-memory state for leak detection."""
        with self._lock:
            return {
                "runs": len(self._runs),
                "agents": len(self._agents),
                "futures_inflight": len(self._futures),
                "by_state": {
                    state: sum(1 for r in self._runs.values() if r.state == state)
                    for state in ("running", "finished", "aborted", "cleaned")
                },
            }

    def secretary(self) -> "Any":
        """Return the lazy-spawned Secretary subprocess (creates on first call)."""
        if self._secretary is None:
            from ..resources.secretary_proc import SecretaryProcess
            with self._lock:
                if self._secretary is None:
                    self._secretary = SecretaryProcess(log_path=self.store.root / "secretary.log")
        return self._secretary

    def shutdown(self) -> None:
        self._shutdown_event.set()
        self.cleanup_idle_runs(force=True)
        self.locks.shutdown()
        self.scheduler.shutdown()
        # Stop the Secretary subprocess if it was ever started.
        if self._secretary is not None:
            try:
                self._secretary.terminate()
            except Exception as exc:
                logger.warning("secretary terminate failed: %s", exc)
        # Flush async trace index writer so on-disk state matches in-memory.
        try:
            self.store.shutdown()
        except Exception as exc:
            logger.warning("trace store shutdown failed: %s", exc)
