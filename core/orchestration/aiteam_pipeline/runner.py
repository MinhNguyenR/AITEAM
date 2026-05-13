from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from aiteamruntime import AgentRuntime

from core.app_state.context_state import update_context_state
from core.domain.delta_brief import DeltaBrief
from core.orchestration.pipeline_artifacts import (
    leader_generate_context,
    secretary_execute_commands,
    tool_curator_generate_tools,
    worker_execute_task,
    write_task_state_json,
)
from core.runtime import session as ws
from utils.file_manager import paths_for_task
from utils.logger import artifact_detail, workflow_event

from .monitor_bridge import RuntimeMonitorBridge
from .workspace_scan import write_workspace_memory

logger = logging.getLogger(__name__)

_PENDING_KEY = "aiteam_runtime_pending_state"
_WORKER_KEYS = ("WORKER_A", "WORKER_B", "WORKER_C", "WORKER_D", "WORKER_E", "DESIGNER")


def _save_pending(state: dict[str, Any]) -> None:
    snap = ws.load_session()
    snap[_PENDING_KEY] = dict(state)
    ws.save_session(snap)


def _load_pending() -> dict[str, Any]:
    raw = ws.load_session().get(_PENDING_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def _clear_pending() -> None:
    snap = ws.load_session()
    snap.pop(_PENDING_KEY, None)
    ws.save_session(snap)


def _emit_artifact(runtime: AgentRuntime, run_id: str, agent_id: str, path: str, stage: str) -> None:
    runtime.emit(
        run_id,
        agent_id,
        "artifact_written",
        {"path": path, "name": Path(path).name, "ref": f"file:{Path(path).as_posix()}"},
        stage=stage,
        resource_key=path,
    )


def _extract_section(text: str, title: str) -> str:
    import re

    pattern = re.compile(
        rf"^#+\s*{re.escape(title)}\s*$\n(.*?)(?=^#+\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text or "")
    return match.group(1).strip() if match else ""


def _extract_commands(text: str) -> list[str]:
    import re

    if not text:
        return []
    match = re.search(r"```(?:bash|sh|powershell|ps1)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    body = match.group(1) if match else text
    out: list[str] = []
    for line in body.splitlines():
        item = line.strip().lstrip("-").strip().strip("`")
        if item and not item.startswith("#"):
            out.append(item)
    return out[:12]


def _extract_worker_assignments(context_text: str, tools_text: str = "") -> dict[str, dict[str, Any]]:
    import re

    source = "\n\n".join([_extract_section(context_text, "Worker Assignments"), _extract_section(tools_text, "Worker Assignments")]).strip()
    if not source:
        return {"WORKER_A": {"text": "Implement all code changes from context.md.", "allowed_paths": []}}
    result: dict[str, dict[str, Any]] = {}
    for index, key in enumerate(_WORKER_KEYS):
        start = re.search(rf"\b{key}\b\s*:?", source, re.IGNORECASE)
        if not start:
            continue
        end_pos = len(source)
        for other in _WORKER_KEYS[index + 1 :]:
            nxt = re.search(rf"\b{other}\b\s*:?", source[start.end() :], re.IGNORECASE)
            if nxt:
                end_pos = min(end_pos, start.end() + nxt.start())
        text = source[start.end() : end_pos].strip()
        paths = [p.strip().strip("`") for p in re.findall(r"`([^`]+)`", text)]
        result[key] = {"text": text or f"Work assigned to {key}.", "allowed_paths": paths}
    return result or {"WORKER_A": {"text": source, "allowed_paths": []}}


def _runtime_for(project_root: str) -> AgentRuntime:
    return AgentRuntime(
        cleanup_delay=0,
        idle_timeout=0,
        max_events_per_run=250,
        governor_defaults={"max_events": 250, "max_runtime_seconds": 900, "max_terminal_seconds": 300},
    )


def run_agent_runtime_pipeline(
    brief: DeltaBrief,
    task_text: str,
    project_root: str,
    settings: dict[str, Any] | None = None,
    *,
    inline_progress: bool = False,
) -> str:
    _ = inline_progress
    settings = dict(settings or {})
    run_id = str(getattr(brief, "task_uuid", "") or "ai-team-runtime")
    runtime = _runtime_for(project_root)
    runtime.start_run(run_id=run_id, prompt=task_text, metadata={"workspace": project_root, "pipeline": "ai-team"})
    bridge = RuntimeMonitorBridge(run_id=run_id, project_root=project_root)
    try:
        ws.set_thread_id(run_id)
        ws.set_pipeline_run_id(run_id)
    except Exception:
        pass
    ws.set_workflow_project_root(project_root)
    ws.set_context_accept_status("none")
    ws.set_should_finalize(bool(settings.get("auto_accept_context")))
    ws.set_pipeline_status_message("Dang chay aiteamruntime pipeline...")
    workflow_event("runner", "runtime_start", f"project_root={project_root}")

    bridge.done("ambassador", f"tier={brief.tier}", role="Ambassador")
    runtime.emit(run_id, "Ambassador", "done", {"tier": brief.tier, "selected_leader": brief.selected_leader}, stage="classify")

    state_path = paths_for_task(brief.task_uuid).state_path
    if not state_path.exists():
        state_path = write_task_state_json(brief, task_text, project_root, source_node="ambassador")
    state_artifact = bridge.artifact(state_path, node="ambassador", kind="state", producer="Ambassador")
    bridge.ingest_artifact(state_artifact, kind="runtime_state", producer="Ambassador")
    bridge.done("ambassador", f"tier={brief.tier}", role="Ambassador", artifacts=[state_artifact])
    _emit_artifact(runtime, run_id, "Ambassador", str(state_path), "classify")

    bridge.started("heartbeat", "Scanning workspace", role="Heartbeat", substate="scanning")
    snapshot = runtime.resources.snapshot_workspace(run_id, limit=500)
    runtime.emit(run_id, "Heartbeat", "workspace_snapshot", {"files": snapshot, "count": len(snapshot)}, stage="heartbeat")
    bridge.done("heartbeat", f"{len(snapshot)} file(s)", role="Heartbeat")

    bridge.started("leader_generate", "Generating context.md", role="Leader", substate="thinking")
    runtime.emit(run_id, "Leader", "reasoning", {"file": "state.json", "purpose": "create context.md"}, stage="plan")
    ctx = leader_generate_context(brief, task_text, project_root, quiet=True, stream_to_monitor=True)
    if ctx is None:
        runtime.emit(run_id, "Leader", "error", {"reason": "leader failed or no_context"}, status="error", stage="plan")
        bridge.error("leader_generate", "leader failed or no_context", role="Leader")
        ws.set_pipeline_graph_failed(True)
        return "failed"
    ctx_artifact = bridge.artifact(ctx, node="leader_generate", kind="context", producer="Leader")
    bridge.ingest_artifact(ctx_artifact, kind="context", producer="Leader")
    _emit_artifact(runtime, run_id, "Leader", str(ctx), "plan")
    bridge.done("leader_generate", str(ctx), role="Leader", artifacts=[ctx_artifact])

    pending = {
        "run_id": run_id,
        "task_text": task_text,
        "project_root": project_root,
        "brief_dict": brief.model_dump(),
        "context_path": str(ctx),
    }
    if not settings.get("auto_accept_context"):
        _save_pending(pending)
        ws.set_paused_for_review(True, str(ctx))
        ws.set_last_node("human_context_gate")
        ws.set_pipeline_paused_at_gate(True)
        ws.set_context_accept_status("pending")
        bridge.started("human_context_gate", "Doi review", role="HumanGate", substate="waiting", artifacts=[ctx_artifact])
        runtime.emit(run_id, "HumanGate", "question", {"context_path": str(ctx), "question": "Approve context.md?"}, status="waiting", stage="approve")
        return "paused"
    return _continue_after_context(runtime, pending)


def resume_agent_runtime_pipeline() -> bool:
    pending = _load_pending()
    if not pending:
        return False
    runtime = _runtime_for(str(pending.get("project_root") or ""))
    run_id = str(pending.get("run_id") or "")
    project_root = str(pending.get("project_root") or "")
    runtime.resume_run(run_id, metadata={"workspace": project_root})
    ws.set_phase_running()
    ws.set_pipeline_paused_at_gate(False)
    ws.set_paused_for_review(False)
    ws.set_pipeline_active_step("human_context_gate")
    runtime.emit(run_id, "HumanGate", "answered", {"answer": "approved"}, stage="approve")
    outcome = _continue_after_context(runtime, pending)
    return outcome == "completed"


def _continue_after_context(runtime: AgentRuntime, state: dict[str, Any]) -> str:
    run_id = str(state["run_id"])
    project_root = str(state["project_root"])
    brief = DeltaBrief.model_validate(state["brief_dict"])
    bridge = RuntimeMonitorBridge(run_id=run_id, project_root=project_root)
    ctx = Path(str(state["context_path"]))
    if not ctx.exists():
        runtime.emit(run_id, "HumanGate", "error", {"reason": "context.md missing after approval"}, status="error", stage="approve")
        bridge.error("human_context_gate", "context.md missing after approval", role="HumanGate")
        ws.set_pipeline_graph_failed(True)
        return "failed"

    bridge.done("human_context_gate", "approved", role="HumanGate", artifacts=[bridge.artifact(ctx, node="human_context_gate", kind="context", producer="Leader")])
    bridge.started("tool_curator", "Writing tools.md", role="Tool Curator", substate="writing")
    tools = tool_curator_generate_tools(ctx, quiet=True)
    if tools is None:
        runtime.emit(run_id, "ToolCurator", "error", {"reason": "tools.md generation failed"}, status="error", stage="tooling")
        bridge.error("tool_curator", "tools.md generation failed", role="Tool Curator")
        ws.set_pipeline_graph_failed(True)
        return "failed"
    tools_artifact = bridge.artifact(tools, node="tool_curator", kind="tools", producer="ToolCurator")
    bridge.ingest_artifact(tools_artifact, kind="tools", producer="ToolCurator")
    _emit_artifact(runtime, run_id, "ToolCurator", str(tools), "tooling")
    bridge.done("tool_curator", str(tools), role="Tool Curator", artifacts=[tools_artifact])

    context_text = ctx.read_text(encoding="utf-8", errors="replace")
    tools_text = Path(tools).read_text(encoding="utf-8", errors="replace") if Path(tools).exists() else ""
    setup_commands = _extract_commands(_extract_section(tools_text, "Setup Commands")) or _extract_commands(_extract_section(context_text, "Terminal Setup Commands"))
    validation_commands = _extract_commands(_extract_section(tools_text, "Validation Commands")) or _extract_commands(_extract_section(context_text, "Validation Commands"))
    assignments = _extract_worker_assignments(context_text, tools_text)

    bridge.started("secretary_setup", "Running setup commands", role="Secretary", substate="using")
    setup_result = secretary_execute_commands(ctx, tools, project_root, commands=setup_commands)
    runtime.emit(run_id, "Secretary", "setup_done", setup_result, stage="setup")
    bridge.done("secretary_setup", f"{len(setup_result.get('commands_run', []))} command(s)", role="Secretary")

    bridge.started("compact_worker", "Scanning codebase", role="Compact Worker", substate="scanning")
    memory = write_workspace_memory(project_root, reason="after secretary setup")
    memory_artifacts = [
        bridge.artifact(memory["codebase_path"], node="compact_worker", kind="codebase", producer="CompactWorker"),
        bridge.artifact(memory["memory_path"], node="compact_worker", kind="memory", producer="CompactWorker"),
    ]
    for artifact in memory_artifacts:
        bridge.ingest_artifact(artifact, kind=str(artifact.get("kind") or "memory"), producer="CompactWorker")
        _emit_artifact(runtime, run_id, "CompactWorker", str(artifact["path"]), "memory")
    bridge.done("compact_worker", f"{memory['files']} file(s)", role="Compact Worker", artifacts=memory_artifacts)

    worker_results: dict[str, dict[str, Any]] = {}
    update_count = 0
    with ThreadPoolExecutor(max_workers=min(5, max(1, len(assignments)))) as pool:
        futures = {}
        for worker_key, assignment in assignments.items():
            work_item_id = f"wi-{worker_key.lower()}"
            payload = {
                "id": work_item_id,
                "title": assignment.get("text") or worker_key,
                "assigned_worker": worker_key,
                "allowed_paths": list(assignment.get("allowed_paths") or []),
                "depends_on": [],
                "timeout": 120,
            }
            runtime.emit(run_id, "ToolCurator", "assigned", {"work_item": payload, "assigned_worker": worker_key}, stage="work", work_item_id=work_item_id, assignment=payload)
            bridge.started(worker_key, "Implementing code changes", role=worker_key, substate="writing", work_item_id=work_item_id)
            futures[pool.submit(worker_execute_task, ctx, tools, project_root, worker_key, brief.task_uuid, str(assignment.get("text") or ""), list(assignment.get("allowed_paths") or []))] = (worker_key, work_item_id)
        for future in as_completed(futures):
            worker_key, work_item_id = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                result = {"worker_key": worker_key, "files_written": [], "errors": [str(exc)]}
            worker_results[worker_key] = result
            files_written = list(result.get("files_written") or [])
            update_count += len(files_written)
            status = "error" if result.get("errors") else "done"
            if status == "error":
                runtime.emit(run_id, worker_key, "worker_failed", result, status="error", stage="work", work_item_id=work_item_id)
                bridge.error(worker_key, "; ".join(map(str, result.get("errors") or []))[:300] or "worker failed", role=worker_key, work_item_id=work_item_id)
            else:
                runtime.emit(run_id, worker_key, "done", result, stage="work", work_item_id=work_item_id)
                file_artifacts = [bridge.artifact(path, node=worker_key, kind="code", producer=worker_key) for path in files_written]
                bridge.done(worker_key, f"{len(files_written)} files written", role=worker_key, artifacts=file_artifacts, work_item_id=work_item_id)
            if update_count and update_count % 4 == 0:
                memory = write_workspace_memory(project_root, reason="periodic worker update")
                periodic_artifacts = [
                    bridge.artifact(memory["codebase_path"], node="compact_worker", kind="codebase", producer="CompactWorker"),
                    bridge.artifact(memory["memory_path"], node="compact_worker", kind="memory", producer="CompactWorker"),
                ]
                for artifact in periodic_artifacts:
                    bridge.ingest_artifact(artifact, kind=str(artifact.get("kind") or "memory"), producer="CompactWorker")
                runtime.emit(run_id, "CompactWorker", "artifact_written", memory, stage="memory")

    bridge.started("secretary", "Running validation commands", role="Secretary", substate="using")
    validation = secretary_execute_commands(ctx, tools, project_root, commands=validation_commands)
    runtime.emit(run_id, "Secretary", "validated", validation, stage="validate")
    passed = sum(1 for item in validation.get("commands_run", []) if item.get("success"))
    bridge.done("secretary", f"{passed}/{len(validation.get('commands_run', []))} passed", role="Secretary")

    bridge.started("finalize_phase1", "Finalize", role="Runtime", substate="finalizing")
    runtime.emit(run_id, "runtime", "finalized", {"workers": worker_results, "validation": validation}, stage="finalize")
    try:
        update_context_state("completed", ctx, reason="aiteamruntime_workflow_completed", task_uuid=brief.task_uuid)
    except Exception:
        logger.debug("context state update skipped", exc_info=True)
    ws.set_pipeline_run_finished(True)
    ws.set_pipeline_active_step("idle")
    ws.set_pipeline_stop_phase("idle")
    if ws.get_context_accept_status() not in {"accepted", "deferred"}:
        ws.set_context_accept_status("none")
    bridge.done("finalize_phase1", "completed", role="Runtime")
    _clear_pending()
    workflow_event("runner", "runtime_completed", artifact_detail(ctx, task_id=brief.task_uuid, producer_node="runner"))
    return "completed"


__all__ = ["run_agent_runtime_pipeline", "resume_agent_runtime_pipeline"]
