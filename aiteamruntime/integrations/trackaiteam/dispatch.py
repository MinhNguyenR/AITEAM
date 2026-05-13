from __future__ import annotations

from typing import Any

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext

from .dag import validate_dag, work_items_from_dag


def latest_dag(events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in reversed(events):
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        dag = payload.get("dag")
        if isinstance(dag, dict) and isinstance(dag.get("work_items"), list):
            return dag
        plan = payload.get("plan") if isinstance(payload.get("plan"), dict) else {}
        dag = plan.get("dag")
        if isinstance(dag, dict) and isinstance(dag.get("work_items"), list):
            return dag
    return {}


def _work_item_id(event: dict[str, Any]) -> str:
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    assignment = event.get("assignment") if isinstance(event.get("assignment"), dict) else {}
    return str(event.get("work_item_id") or payload.get("work_item_id") or assignment.get("id") or "")


def _validated(events: list[dict[str, Any]]) -> set[str]:
    return {_work_item_id(event) for event in events if event.get("kind") == "validated" and _work_item_id(event)}


def _assigned(events: list[dict[str, Any]]) -> set[str]:
    return {
        _work_item_id(event)
        for event in events
        if event.get("kind") == "assigned" and event.get("agent_id") == "Leader" and _work_item_id(event)
    }


def _active(events: list[dict[str, Any]], done: set[str]) -> set[str]:
    active = _assigned(events) - done
    for event in events:
        if event.get("kind") in {"worker_failed", "abort_task"}:
            active.discard(_work_item_id(event))
    return active


def latest_artifact_paths(events: list[dict[str, Any]]) -> tuple[str, str]:
    context_path = ""
    tools_path = ""
    for event in reversed(events):
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        context_path = context_path or str(payload.get("context_path") or "")
        tools_path = tools_path or str(payload.get("tools_path") or "")
        if context_path and tools_path:
            break
    return context_path, tools_path


def leader_dispatch_agent(ctx: AgentContext, event: AgentEvent) -> None:
    events = ctx.runtime.store.read_events(ctx.run_id)
    dag = latest_dag(events)
    if not dag:
        ctx.emit("blocked", {"reason": "Leader dispatch requires dag.json", "trigger": event.kind}, status="blocked", stage="work", role_state="blocked")
        return
    errors = validate_dag(dag)
    if errors:
        ctx.emit("blocked", {"reason": "invalid dag.json", "errors": errors}, status="blocked", stage="work", role_state="blocked")
        return
    items = work_items_from_dag(dag)
    done = _validated(events)
    active = _active(events, done)
    all_ids = {str(item.get("id") or "") for item in items if str(item.get("id") or "")}
    if all_ids and all_ids.issubset(done):
        ctx.emit("dag_complete", {"dag": dag, "completed": sorted(done)}, stage="finalize", role_state="done")
        return
    if active:
        ctx.emit("leader_dispatch", {"state": "waiting_for_active_workers", "active": sorted(active), "trigger": event.kind}, status="waiting", stage="work", role_state="waiting")
        return
    assigned = _assigned(events)
    context_path, tools_path = latest_artifact_paths(events)
    for item in items:
        item_id = str(item.get("id") or "")
        if not item_id or item_id in done or item_id in assigned:
            continue
        deps = {str(dep) for dep in item.get("depends_on") or [] if str(dep)}
        if deps and not deps.issubset(done):
            continue
        payload: dict[str, Any] = {
            "stage": "work",
            "work_item": item,
            "assigned_worker": item.get("assigned_worker"),
            "allowed_paths": item.get("allowed_paths") or [],
            "context_path": context_path,
            "tools_path": tools_path,
            "dispatch_authority": "Leader",
            "dispatch_trigger": event.kind,
        }
        ctx.emit("assigned", payload, stage="work", work_item_id=item_id, assignment=item, role_state="waiting")
        ctx.emit("leader_dispatch", {"state": "released_work_item", "released": [item_id], "trigger": event.kind}, status="waiting", stage="work", role_state="waiting")
        return
    ctx.emit("leader_dispatch", {"state": "no_ready_work", "done": sorted(done)}, stage="work", role_state="done")
