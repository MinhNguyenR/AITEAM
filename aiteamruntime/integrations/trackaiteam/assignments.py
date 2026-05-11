from __future__ import annotations

from typing import Any

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext, WorkItem

from .config import WORKER_REGISTRY
from .setup import command_payload


def build_assignments(ctx: AgentContext, work_items: list[WorkItem]) -> list[dict[str, Any]]:
    assignments: list[dict[str, Any]] = []
    claimed_files: dict[str, str] = {}
    worker_order = list(WORKER_REGISTRY)
    for index, item in enumerate(work_items):
        worker = worker_order[index % len(worker_order)]
        conflict = next((path for path in item.allowed_paths if path in claimed_files), "")
        if conflict:
            ctx.emit(
                "blocked",
                {
                    "resource_type": "file",
                    "resource_key": conflict,
                    "owner_agent_id": claimed_files[conflict],
                    "reason": "file already assigned; queued for serialization",
                    "work_item_id": item.id,
                },
                status="blocked",
                stage="tooling",
                work_item_id=item.id,
                resource_key=conflict,
            )
            worker = claimed_files[conflict]
        for path in item.allowed_paths:
            claimed_files.setdefault(path, worker)
        item.assigned_worker = worker
        assignment = item.to_dict()
        assignment["reason"] = WORKER_REGISTRY[worker]["reason"]
        assignments.append(assignment)
    return assignments


def emit_assignments(ctx: AgentContext, assignments: list[dict[str, Any]], *, gate_id: str = "") -> None:
    for assignment in assignments:
        payload = {
            "stage": "work",
            "work_item": assignment,
            "assigned_worker": assignment.get("assigned_worker"),
            "allowed_paths": assignment.get("allowed_paths") or [],
        }
        if gate_id:
            payload["setup_gate_id"] = gate_id
        ctx.emit(
            "assigned",
            payload,
            stage="work",
            work_item_id=str(assignment.get("id") or ""),
            assignment=assignment,
            role_state="waiting",
        )


def request_setup_command(ctx: AgentContext, gate_id: str, commands: list[dict[str, Any]], index: int) -> None:
    if index < 0 or index >= len(commands):
        return
    payload = command_payload(commands[index], "setup")
    payload["gate_id"] = gate_id
    payload["setup_index"] = index
    payload["setup_total"] = len(commands)
    payload["creates"] = list(commands[index].get("creates") or [])
    ctx.emit("setup_requested", payload, stage="setup", role_state="waiting")


def release_assignments_after_setup(ctx: AgentContext, event: AgentEvent) -> None:
    gate_id = str(event.payload.get("gate_id") or "")
    if not gate_id:
        return
    events = ctx.runtime.store.read_events(ctx.run_id)
    if any((item.get("payload") or {}).get("setup_gate_id") == gate_id and item.get("kind") == "assigned" for item in events):
        return
    gate = next(
        (
            item
            for item in reversed(events)
            if item.get("kind") == "progress"
            and item.get("agent_id") == "Tool Curator"
            and (item.get("payload") or {}).get("gate_id") == gate_id
        ),
        None,
    )
    if gate is None:
        return
    payload = gate.get("payload") or {}
    commands = payload.get("setup_commands") if isinstance(payload.get("setup_commands"), list) else []
    assignments = payload.get("assignments") if isinstance(payload.get("assignments"), list) else []
    results = [
        item
        for item in events
        if item.get("kind") == "setup_done" and (item.get("payload") or {}).get("gate_id") == gate_id
    ]
    if any(str(item.get("status") or "") in {"error", "timeout"} for item in results):
        ctx.emit("blocked", {"gate_id": gate_id, "reason": "setup failed; workers not released"}, status="blocked", stage="setup", role_state="blocked")
        return
    if len(results) < len(commands):
        requested_indexes = {
            int((item.get("payload") or {}).get("setup_index") or 0)
            for item in events
            if item.get("kind") == "setup_requested" and (item.get("payload") or {}).get("gate_id") == gate_id
        }
        next_index = len(results)
        if next_index not in requested_indexes:
            request_setup_command(ctx, gate_id, commands, next_index)
        ctx.emit(
            "progress",
            {"gate_id": gate_id, "state": "waiting_for_setup", "done": len(results), "total": len(commands)},
            status="waiting",
            stage="setup",
            role_state="waiting",
        )
        return
    ctx.emit("progress", {"gate_id": gate_id, "state": "setup_complete_releasing_workers"}, stage="setup", role_state="done")
    emit_assignments(ctx, [dict(item) for item in assignments if isinstance(item, dict)], gate_id=gate_id)
