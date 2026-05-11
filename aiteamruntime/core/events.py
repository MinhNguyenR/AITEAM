from __future__ import annotations

from dataclasses import dataclass, field
import time
import uuid
from typing import Any

EVENT_KINDS = frozenset(
    {
        # Pipeline activity
        "blocked",
        "classifying",
        "routing",
        "reading",
        "reasoning",
        "writing",
        "model_requested",
        "model_response",
        "terminal_requested",
        "terminal_running",
        "terminal_result",
        "file_update",
        "file_create",
        "assigned",
        "setup_requested",
        "setup_done",
        "worker_failed",
        "reassigned",
        "validated",
        "finalized",
        "schema_error",
        "schema_repair_requested",
        "schema_repaired",
        "abort_task",
        "overseer_action",
        "hydrated",
        "token_usage",
        "question",
        "answered",
        "done",
        "error",
        "abort",
        # Lifecycle (Phase 1)
        "run_started",
        "run_finished",
        "run_aborted",
        "cleanup_complete",
        # Node coordination (Phase 4)
        "node_locked",
        "node_released",
        "node_blocked",
        # Observability (Phase 1, 6, 7)
        "heartbeat",
        "progress",
        "worker_pool_full",
        "quota_exceeded",
        # Secretary subprocess (Phase 2)
        "secretary_command",
        "secretary_result",
    }
)

EVENT_STATUSES = frozenset(
    {"ok", "running", "waiting", "blocked", "done", "error", "aborted", "reused", "timeout", "deadlock"}
)


@dataclass(frozen=True)
class AgentEvent:
    run_id: str
    agent_id: str
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)
    status: str = "ok"
    event_id: str = ""
    parent_event_id: str = ""
    correlation_id: str = ""
    sequence: int = 0
    attempt: int = 0
    depth: int = 0
    dedupe_key: str = ""
    stage: str = ""
    work_item_id: str = ""
    resource_key: str = ""
    duration_ms: int = 0
    role_state: str = ""
    assignment: dict[str, Any] = field(default_factory=dict)
    retry_of: str = ""

    def __post_init__(self) -> None:
        if self.kind not in EVENT_KINDS:
            raise ValueError(f"unknown agent event kind: {self.kind}")
        if not self.run_id:
            raise ValueError("run_id is required")
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if self.status not in EVENT_STATUSES:
            raise ValueError(f"unknown agent event status: {self.status}")
        if not self.event_id:
            object.__setattr__(self, "event_id", uuid.uuid4().hex)
        if not self.correlation_id:
            object.__setattr__(self, "correlation_id", self.event_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "parent_event_id": self.parent_event_id,
            "correlation_id": self.correlation_id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "kind": self.kind,
            "payload": dict(self.payload or {}),
            "ts": float(self.ts),
            "status": self.status,
            "sequence": int(self.sequence),
            "attempt": int(self.attempt),
            "depth": int(self.depth),
            "dedupe_key": self.dedupe_key,
            "stage": self.stage,
            "work_item_id": self.work_item_id,
            "resource_key": self.resource_key,
            "duration_ms": int(self.duration_ms),
            "role_state": self.role_state,
            "assignment": dict(self.assignment or {}),
            "retry_of": self.retry_of,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentEvent":
        return cls(
            run_id=str(data.get("run_id") or ""),
            agent_id=str(data.get("agent_id") or ""),
            kind=str(data.get("kind") or ""),
            payload=dict(data.get("payload") or {}),
            ts=float(data.get("ts") or time.time()),
            status=str(data.get("status") or "ok"),
            event_id=str(data.get("event_id") or ""),
            parent_event_id=str(data.get("parent_event_id") or ""),
            correlation_id=str(data.get("correlation_id") or ""),
            sequence=int(data.get("sequence") or 0),
            attempt=int(data.get("attempt") or 0),
            depth=int(data.get("depth") or 0),
            dedupe_key=str(data.get("dedupe_key") or ""),
            stage=str(data.get("stage") or ""),
            work_item_id=str(data.get("work_item_id") or ""),
            resource_key=str(data.get("resource_key") or ""),
            duration_ms=int(data.get("duration_ms") or 0),
            role_state=str(data.get("role_state") or ""),
            assignment=dict(data.get("assignment") or {}),
            retry_of=str(data.get("retry_of") or ""),
        )
