from __future__ import annotations

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext, WorkItem

from .config import WORKER_REGISTRY
from .setup import command_payload


def build_assignments(ctx: AgentContext, work_items: list[WorkItem]) -> list[dict]:
    assignments: list[dict] = []
    claimed_files: dict[str, str] = {}
    worker_order = list(WORKER_REGISTRY)
    for index, item in enumerate(work_items):
        worker = item.assigned_worker if item.assigned_worker in WORKER_REGISTRY else worker_order[index % len(worker_order)]
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


def request_setup_command(ctx: AgentContext, gate_id: str, commands: list[dict], index: int) -> None:
    if index < 0 or index >= len(commands):
        return
    payload = command_payload(commands[index], "setup")
    payload["gate_id"] = gate_id
    payload["setup_index"] = index
    payload["setup_total"] = len(commands)
    payload["creates"] = list(commands[index].get("creates") or [])
    payload["tools_path"] = str(commands[index].get("tools_path") or "")
    payload["context_path"] = str(commands[index].get("context_path") or "")
    cwd = str(payload.get("cwd") or ".")
    if cwd and cwd != ".":
        try:
            ctx.runtime.resources.resolve_workspace_path(ctx.run_id, cwd).mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
    ctx.emit("setup_requested", payload, stage="setup", role_state="waiting")


def _join_rel(base: str, leaf: str) -> str:
    base = str(base or ".").replace("\\", "/").strip("/")
    leaf = str(leaf or "").replace("\\", "/").strip("/")
    if not base or base == ".":
        return leaf
    return f"{base}/{leaf}" if leaf else base


def release_assignments_after_setup(ctx: AgentContext, event: AgentEvent) -> None:
    gate_id = str(event.payload.get("gate_id") or "")
    if not gate_id:
        return
    events = ctx.runtime.store.read_events(ctx.run_id)
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
    results = [item for item in events if item.get("kind") == "setup_done" and (item.get("payload") or {}).get("gate_id") == gate_id]
    if any(str(item.get("status") or "") in {"error", "timeout"} for item in results):
        failed = next((item for item in reversed(results) if str(item.get("status") or "") in {"error", "timeout"}), results[-1])
        ctx.emit(
            "blocked",
            {"gate_id": gate_id, "reason": "setup failed; workers not released", "setup_error": failed.get("payload") or {}},
            status="blocked",
            stage="setup",
            role_state="blocked",
        )
        return
    if len(results) < len(commands):
        request_setup_command(ctx, gate_id, commands, len(results))
        ctx.emit("progress", {"gate_id": gate_id, "state": "waiting_for_setup", "done": len(results), "total": len(commands)}, status="waiting", stage="setup", role_state="waiting")
        return
    latest_payload = (results[-1].get("payload") if results else {}) or {}
    latest_cwd = str(latest_payload.get("cwd") or ".")
    missing = [
        path
        for path in latest_payload.get("creates") or []
        if path and not ctx.runtime.resources.resolve_workspace_path(ctx.run_id, _join_rel(latest_cwd, str(path))).exists()
    ]
    if missing:
        ctx.emit("blocked", {"gate_id": gate_id, "reason": "setup created files are missing", "missing_creates": missing}, status="blocked", stage="setup", role_state="blocked")
        return
    ctx.emit(
        "setup_verified",
        {
            "gate_id": gate_id,
            "creates": list(latest_payload.get("creates") or []),
            "context_path": str(payload.get("context_path") or ""),
            "tools_path": str(payload.get("tools_path") or ""),
            "assignments": [dict(item) for item in payload.get("assignments") or [] if isinstance(item, dict)],
            "dag": payload.get("dag") if isinstance(payload.get("dag"), dict) else {},
        },
        stage="setup",
        role_state="done",
    )
    ctx.emit("progress", {"gate_id": gate_id, "state": "setup_complete_waiting_for_leader_dispatch"}, stage="setup", role_state="done")
