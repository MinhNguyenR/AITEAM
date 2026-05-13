from __future__ import annotations

import json

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext, WorkItem
from core.domain.prompts.tool_curator import TOOL_CURATOR_SYSTEM_PROMPT

from ..assignments import build_assignments, release_assignments_after_setup, request_setup_command
from ..config import WORKER_REGISTRY
from ..model import chat_completion, model_meta, model_timeout, real_model_enabled
from ..setup import format_setup_commands, safe_setup_commands, workspace_snapshot
from ..utils import model_error, write_run_artifact


def tool_curator_agent(ctx: AgentContext, event: AgentEvent) -> None:
    if event.kind == "setup_finished":
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
    role_key = "TOOL_CURATOR"
    meta = model_meta(role_key)
    ctx.emit("reading", {"file": "runtime plan", "purpose": "write tools.md and setup gate", **meta}, stage="tooling", role_state="running")
    ctx.emit("model_requested", {"operation": "select_tools", "timeout_s": model_timeout(), **meta}, stage="tooling", role_state="running")
    ctx.emit("progress", {"state": "tool_curator_model_running", "operation": "select_tools", **meta}, status="running", stage="tooling", role_state="running")
    try:
        tool_content = chat_completion(
            role_key=role_key,
            system=TOOL_CURATOR_SYSTEM_PROMPT,
            user=(
                "Write tools.md from this Leader plan. Include Secretary-only setup commands if a project scaffold is needed. "
                "Do not assign or release workers.\n\n"
                f"{json.dumps({'plan': plan, 'worker_registry': WORKER_REGISTRY, 'workspace_snapshot': workspace_snapshot(ctx)}, ensure_ascii=False, indent=2)}"
            ),
            max_tokens=1200,
        )
    except Exception as exc:
        model_error(ctx, stage="tooling", exc=exc)
        ctx.runtime.request_abort(ctx.run_id, "tool curator model failed")
        return
    ctx.emit("model_response", {"operation": "select_tools", "chars": len(tool_content), **meta}, stage="tooling", role_state="done")
    project_root = str(plan.get("project_root") or (plan.get("dag") or {}).get("project_root") or "app")
    setup_commands = safe_setup_commands(ctx, plan, [])
    for command in setup_commands:
        command["cwd"] = project_root
    if "## Setup Commands" not in tool_content:
        tool_content = tool_content.rstrip() + "\n\n## Setup Commands\n" + format_setup_commands(setup_commands)
    try:
        tool_path, tool_full_path, tool_ref = write_run_artifact(ctx, "tools.md", tool_content, project_dir=project_root)
        ctx.emit("artifact_written", {"path": tool_path, "absolute_path": str(tool_full_path), "ref_id": tool_ref, "storage": "runtime_cache"}, stage="tooling")
    except Exception as exc:
        ctx.emit("worker_failed", {"reason": str(exc), "target": "tools.md"}, status="error", stage="tooling")
        return
    assignments = build_assignments(ctx, work_items)
    for command in setup_commands:
        command["tools_path"] = tool_path
    context_path = str(plan.get("context_path") or "")
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
                "context_path": context_path,
                "tools_path": tool_path,
                "dag": plan.get("dag") if isinstance(plan.get("dag"), dict) else {},
            },
            status="waiting",
            stage="setup",
            role_state="waiting",
        )
        request_setup_command(ctx, gate_id, setup_commands, 0)
    else:
        ctx.emit(
            "setup_verified",
            {
                "gate_id": "",
                "context_path": context_path,
                "tools_path": tool_path,
                "assignments": assignments,
                "dag": plan.get("dag") if isinstance(plan.get("dag"), dict) else {},
                "reason": "no setup commands required",
            },
            stage="setup",
            role_state="done",
        )
    ctx.emit("done", {"stage": "tooling", "assignments": assignments, "plan": plan, "setup_commands": setup_commands, "tools_path": tool_path}, stage="tooling")
