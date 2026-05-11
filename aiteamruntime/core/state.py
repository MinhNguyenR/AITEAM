from __future__ import annotations

from dataclasses import dataclass, field
import time
import uuid
from typing import Any, Callable

from .contracts import AgentContract
from .events import AgentEvent
from .governor import GovernorState

TriggerPredicate = Callable[[AgentEvent], bool]
AgentHandler = Callable[["AgentContext", AgentEvent], object]


@dataclass(frozen=True)
class AgentSpec:
    agent_id: str
    handler: AgentHandler
    trigger: TriggerPredicate
    label: str = ""
    lane: str = ""
    triggers_kinds: frozenset[str] = frozenset()
    contract: AgentContract | None = None
    """Optional whitelist of event kinds this spec ever matches.

    Empty means the spec is catch-all and is checked against every event.
    Declaring kinds lets the runtime index specs by event kind.
    """

    def matches(self, event: AgentEvent) -> bool:
        return bool(self.trigger(event))


@dataclass
class WorkItem:
    id: str
    title: str
    assigned_worker: str = ""
    allowed_paths: list[str] = field(default_factory=list)
    status: str = "queued"
    attempt: int = 0
    timeout: float = 30.0
    depends_on: list[str] = field(default_factory=list)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "WorkItem":
        return cls(
            id=str(payload.get("id") or payload.get("work_item_id") or uuid.uuid4().hex[:8]),
            title=str(payload.get("title") or payload.get("task") or "Work item"),
            assigned_worker=str(payload.get("assigned_worker") or ""),
            allowed_paths=[str(path) for path in payload.get("allowed_paths") or payload.get("files") or []],
            status=str(payload.get("status") or "queued"),
            attempt=int(payload.get("attempt") or 0),
            timeout=float(payload.get("timeout") or 30.0),
            depends_on=[str(dep) for dep in payload.get("depends_on") or []],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "assigned_worker": self.assigned_worker,
            "allowed_paths": list(self.allowed_paths),
            "status": self.status,
            "attempt": self.attempt,
            "timeout": self.timeout,
            "depends_on": list(self.depends_on),
        }


@dataclass
class RunState:
    """All per-run mutable state. Lives until ``cleanup_run`` is called."""

    run_id: str
    started_at: float = field(default_factory=time.time)
    last_event_at: float = field(default_factory=time.time)
    state: str = "running"  # running | finished | aborted | cleaned
    seq: int = 0
    event_count: int = 0
    finalize_at: float = 0.0  # 0 = no finalize scheduled
    pool_full_last: float = 0.0  # last time worker_pool_full was emitted
    scheduled_events: set[str] = field(default_factory=set)
    work_items: dict[str, WorkItem] = field(default_factory=dict)
    worker_busy: dict[str, str] = field(default_factory=dict)
    governor: GovernorState | None = None
