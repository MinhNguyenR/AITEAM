from __future__ import annotations

import json
from typing import Any

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext, WorkItem

from ..assignments import build_assignments, emit_assignments, release_assignments_after_setup, request_setup_command
from ..config import WORKER_REGISTRY
from ..model import chat_json, model_meta, real_model_enabled
from ..setup import format_setup_commands, safe_setup_commands, workspace_snapshot
from ..utils import model_error, sleep, tool_file_path, write_workspace_text


def tool_curator_agent(ctx: AgentContext, event: AgentEvent) -> None:
    if event.kind == "setup_done":
        release_assignments_after_setup(ctx, event)
        return
    if not real_model_enabled():
        ctx.emit(
            "error",
            {"stage": "tooling", "type": "ModelNotReady", "message": "OPENROUTER_API_KEY is required for Tool Curator"},
            status="error",
            stage="tooling",
            role_state="error",
        )
        ctx.runtime.request_abort(ctx.run_id, "tool curator model provider is not configured")
        return
    plan = dict(event.payload.get("plan") or {})
    work_items = [WorkItem.from_payload(item) for item in plan.get("work_items") or []]
    ctx.emit("reading", {"file": "runtime plan", "purpose": "select tools and compatible workers"}, stage="tooling")
    sleep(0.01)
    tool_notes: dict[str, Any] = {
        "tools": [],
        "worker_registry": WORKER_REGISTRY,
        "assignment_notes": "",
        "project_setup_commands": [],
    }
    role_key = "TOOL_CURATOR"
    try:
        model_tools = chat_json(
            role_key=role_key,
            system=(
                "You are Tool Curator. Return JSON only with keys: tools, assignment_notes, project_setup_commands. "
                "project_setup_commands are Secretary-only commands needed before workers start. "
                "Only include setup/scaffold commands when the workspace does not already contain the required project scaffold. "
                "Do not put validation commands or worker commands in project_setup_commands."
            ),
            user=json.dumps(
                {
                    "plan": plan,
                    "worker_registry": WORKER_REGISTRY,
                    "workspace_snapshot": workspace_snapshot(ctx),
                },
                ensure_ascii=False,
                indent=2,
            ),
            max_tokens=1200,
        )
    except Exception as exc:
        model_error(ctx, stage="tooling", exc=exc)
        ctx.runtime.request_abort(ctx.run_id, "tool curator model failed")
        return
    tools = model_tools.get("tools") if isinstance(model_tools.get("tools"), list) else tool_notes["tools"]
    tool_notes = {
        "tools": [str(tool) for tool in tools],
        "worker_registry": WORKER_REGISTRY,
        "assignment_notes": str(model_tools.get("assignment_notes") or ""),
        "project_setup_commands": safe_setup_commands(ctx, plan, model_tools.get("project_setup_commands")),
        **model_meta(role_key),
    }
    ctx.emit("writing", {"file": "tool choices", **tool_notes}, stage="tooling")
    tool_path = tool_file_path(plan)
    tool_content = (
        "Tools selected by Tool Curator\n"
        "\nSecretary-only setup\n"
        + format_setup_commands(tool_notes.get("project_setup_commands") or [])
        + "\nWorker-facing tools\n"
        + "".join(f"- {tool}\n" for tool in tool_notes["tools"])
        + f"\nAssignment notes:\n{tool_notes.get('assignment_notes') or 'Assigned by worker registry.'}\n"
    )
    try:
        tool_full_path = write_workspace_text(ctx, tool_path, tool_content)
        ctx.emit("file_create", {"path": tool_path, "absolute_path": str(tool_full_path), "added_lines": len(tool_content.splitlines())}, stage="tooling")
    except Exception as exc:
        ctx.emit("worker_failed", {"reason": str(exc), "target": tool_path}, status="error", stage="tooling")
        return
    assignments = build_assignments(ctx, work_items)
    setup_commands = [command for command in tool_notes.get("project_setup_commands") or [] if isinstance(command, dict)]
    if setup_commands:
        gate_id = f"setup-{event.event_id[:12]}"
        ctx.emit(
            "progress",
            {
                "stage": "setup",
                "gate_id": gate_id,
                "state": "waiting_for_secretary",
                "assignments": assignments,
                "setup_commands": setup_commands,
            },
            status="waiting",
            stage="setup",
            role_state="waiting",
        )
        request_setup_command(ctx, gate_id, setup_commands, 0)
    else:
        emit_assignments(ctx, assignments)
    ctx.emit("done", {"stage": "tooling", "assignments": assignments, "plan": plan, "setup_commands": setup_commands}, stage="tooling")
