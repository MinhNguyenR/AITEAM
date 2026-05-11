from __future__ import annotations

import logging
import re
from pathlib import Path

from core.app_state.context_state import update_context_state
from core.runtime import session as ws
from core.domain.delta_brief import DeltaBrief
from utils.file_manager import paths_for_task
from utils.logger import artifact_detail, workflow_event

from .pipeline_artifacts import (
    leader_generate_context,
    secretary_execute_commands,
    tool_curator_generate_tools,
    worker_execute_task,
    write_task_state_json,
)
from .team_state import TeamState

logger = logging.getLogger(__name__)


def brief_from_state(state: TeamState) -> DeltaBrief:
    return DeltaBrief.model_validate(state["brief_dict"])


def node_leader_generate(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("leader_generate")
    ws.update_workflow_node_status("leader_generate", "running", "Dang generate context")
    workflow_event("leader_generate", "enter", "Leader generate context.md")
    ws.set_pipeline_status_message("Leader dang generate context.md (streaming neu bat)...")
    brief = brief_from_state(state)
    ctx = leader_generate_context(
        brief,
        state["original_prompt"],
        state["project_root"],
        quiet=True,
        stream_to_monitor=True,
    )
    if ctx is None:
        workflow_event("leader_generate", "leader_generate_failed", "ctx is None / no_context")
        return {"context_path": None, "leader_failed": True, "state_json_path": None}
    state_path = paths_for_task(brief.task_uuid).state_path
    workflow_event(
        "leader_generate",
        "context_written",
        artifact_detail(ctx, task_id=brief.task_uuid, producer_node="leader_generate"),
    )
    ws.set_pipeline_status_message(f"Da ghi context.md -> {ctx}")
    return {"context_path": str(ctx), "leader_failed": False, "state_json_path": str(state_path)}


def node_human_context_gate(state: TeamState) -> TeamState:
    _ = state
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("human_context_gate")
    ws.update_workflow_node_status("human_context_gate", "running", "Doi review")
    workflow_event("human_context_gate", "enter", "interrupt_before gate")
    ws.set_pipeline_status_message("Tam dung tai human_context_gate - cho review")
    return {}


_WORKER_KEYS = ("WORKER_A", "WORKER_B", "WORKER_C", "WORKER_D", "WORKER_E")


def _extract_section(text: str, title: str) -> str:
    pattern = re.compile(
        rf"^#+\s*{re.escape(title)}\s*$\n(.*?)(?=^#+\s+|\Z)",
        re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(text or "")
    return m.group(1).strip() if m else ""


def _extract_commands(section: str) -> list[str]:
    if not section:
        return []
    m = re.search(r"```(?:bash|sh|powershell|ps1)?\s*(.*?)```", section, re.DOTALL | re.IGNORECASE)
    body = m.group(1) if m else section
    out: list[str] = []
    for line in body.splitlines():
        s = line.strip().lstrip("-").strip()
        if s and not s.startswith("#"):
            out.append(s.strip("`"))
    return out[:12]


def _extract_worker_assignments(context_text: str) -> dict[str, dict]:
    section = _extract_section(context_text, "Worker Assignments")
    if not section:
        return {"WORKER_A": {"text": "Implement all code changes from context.md.", "allowed_paths": []}}
    result: dict[str, dict] = {}
    for idx, key in enumerate(_WORKER_KEYS):
        start = re.search(rf"\b{key}\b\s*:?", section, re.IGNORECASE)
        if not start:
            continue
        end_pos = len(section)
        for other in _WORKER_KEYS[idx + 1:]:
            nxt = re.search(rf"\b{other}\b\s*:?", section[start.end():], re.IGNORECASE)
            if nxt:
                end_pos = min(end_pos, start.end() + nxt.start())
        text = section[start.end():end_pos].strip()
        paths = [p.strip().strip("`") for p in re.findall(r"`([^`]+)`", text)]
        result[key] = {"text": text or f"Work assigned to {key}.", "allowed_paths": paths}
    return result or {"WORKER_A": {"text": section, "allowed_paths": []}}


def _detect_assignment_overlap(assignments: dict[str, dict]) -> list[str]:
    """Return list of paths claimed by more than one worker."""
    from collections import defaultdict
    path_owners: dict[str, list[str]] = defaultdict(list)
    for worker_key, assignment in assignments.items():
        for p in assignment.get("allowed_paths") or []:
            path_owners[p].append(worker_key)
    return [p for p, owners in path_owners.items() if len(owners) > 1]


def node_parallel_prepare(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("parallel_prepare")
    ws.update_workflow_node_status("parallel_prepare", "running", "Preparing parallel roles")
    ctx = state.get("context_path")
    text = Path(ctx).read_text(encoding="utf-8", errors="replace") if ctx and Path(ctx).exists() else ""
    setup_commands = _extract_commands(_extract_section(text, "Terminal Setup Commands"))
    validation_commands = _extract_commands(_extract_section(text, "Validation Commands"))
    assignments = _extract_worker_assignments(text)
    overlaps = _detect_assignment_overlap(assignments)
    if overlaps:
        # Overlapping ownership is unsafe for parallel execution - fall back to single worker.
        logger.warning("parallel_prepare: overlapping file ownership %s - falling back to WORKER_A", overlaps)
        assignments = {"WORKER_A": {"text": text, "allowed_paths": []}}
        ws.update_workflow_node_status("parallel_prepare", "done", "1 worker (overlap fallback)")
    else:
        ws.update_workflow_node_status("parallel_prepare", "done", f"{len(assignments)} worker assignment(s)")
    return {
        "setup_commands": setup_commands,
        "validation_commands": validation_commands,
        "worker_assignments": assignments,
    }


def node_secretary_setup(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("secretary_setup")
    ws.update_workflow_node_status("secretary_setup", "running", "Running setup commands")
    ctx = state.get("context_path")
    commands = list(state.get("setup_commands") or [])
    if not commands and state.get("tools_path"):
        try:
            text = Path(str(state.get("tools_path"))).read_text(encoding="utf-8", errors="replace")
            commands = _extract_commands(_extract_section(text, "Setup Commands"))
            if not commands:
                commands = _extract_commands(text)
        except OSError:
            commands = []
    if not ctx or not commands:
        ws.update_workflow_node_status("secretary_setup", "done", "no setup commands")
        return {"setup_result": {"commands_run": []}}
    result = secretary_execute_commands(ctx, state.get("tools_path"), state.get("project_root", ""), commands=commands)
    ws.update_workflow_node_status("secretary_setup", "done", f"{len(result.get('commands_run', []))} command(s)")
    return {"setup_result": result}


def node_tool_curator(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("tool_curator")
    ws.update_workflow_node_status("tool_curator", "running", "Dang chon tool")
    workflow_event("tool_curator", "enter", "Tool Curator generate tools.md")
    ws.set_pipeline_status_message("Tool Curator dang viet tools.md...")
    ctx = state.get("context_path")
    if not ctx:
        workflow_event("tool_curator", "tool_curator_skipped", "no context_path")
        return {"tools_path": None, "curator_failed": True}
    tools = tool_curator_generate_tools(ctx, quiet=True)
    if tools is None:
        workflow_event("tool_curator", "tool_curator_failed", "generate_tools returned None")
        ws.update_workflow_node_status("tool_curator", "error", "tool curator failed")
        return {"tools_path": None, "curator_failed": True}
    ws.update_workflow_node_status("tool_curator", "done", str(tools))
    workflow_event(
        "tool_curator",
        "tools_written",
        artifact_detail(str(tools), task_id=brief_from_state(state).task_uuid, producer_node="tool_curator"),
    )
    ws.set_pipeline_status_message(f"Da ghi tools.md -> {tools}")
    return {"tools_path": str(tools), "curator_failed": False}


def node_worker(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("worker")
    ws.update_workflow_node_status("worker", "running", "Implementing code changes")
    workflow_event("worker", "enter", "Worker implementing code")
    ws.set_pipeline_status_message("Worker dang implement code changes...")
    ctx = state.get("context_path")
    tools = state.get("tools_path")
    project_root = state.get("project_root", "")
    worker_key = state.get("worker_key", "WORKER_A")
    brief = brief_from_state(state)
    if not ctx:
        workflow_event("worker", "worker_skipped", "no context_path")
        ws.update_workflow_node_status("worker", "error", "no context")
        return {"worker_result": None}
    result = worker_execute_task(ctx, tools, project_root, worker_key, brief.task_uuid)
    files_written = result.get("files_written", [])
    ws.update_workflow_node_status("worker", "done", f"{len(files_written)} files written")
    workflow_event("worker", "worker_done", f"files_written={len(files_written)}")
    ws.set_pipeline_status_message(f"Worker xong: {len(files_written)} files")
    return {"worker_result": result}


def _node_worker_key(state: TeamState, worker_key: str, result_key: str) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step(worker_key.lower())
    ws.update_workflow_node_status(worker_key, "running", "Implementing code changes")
    ctx = state.get("context_path")
    project_root = state.get("project_root", "")
    brief = brief_from_state(state)
    assignment = (state.get("worker_assignments") or {}).get(worker_key)
    if not ctx or not assignment:
        ws.update_workflow_node_status(worker_key, "done", "skipped")
        return {result_key: {"worker_key": worker_key, "skipped": True, "files_written": [], "commands": [], "errors": []}}
    result = worker_execute_task(
        ctx,
        state.get("tools_path"),
        project_root,
        worker_key,
        brief.task_uuid,
        assignment_text=str(assignment.get("text") or ""),
        allowed_paths=list(assignment.get("allowed_paths") or []),
    )
    result["worker_key"] = worker_key
    files_written = result.get("files_written", [])
    ws.update_workflow_node_status(worker_key, "done", f"{len(files_written)} files written")
    workflow_event(worker_key, "worker_done", f"files_written={len(files_written)}")
    return {result_key: result}


def node_worker_a(state: TeamState) -> TeamState:
    return _node_worker_key(state, "WORKER_A", "worker_a_result")


def node_worker_b(state: TeamState) -> TeamState:
    return _node_worker_key(state, "WORKER_B", "worker_b_result")


def node_worker_c(state: TeamState) -> TeamState:
    return _node_worker_key(state, "WORKER_C", "worker_c_result")


def node_worker_d(state: TeamState) -> TeamState:
    return _node_worker_key(state, "WORKER_D", "worker_d_result")


def node_worker_e(state: TeamState) -> TeamState:
    return _node_worker_key(state, "WORKER_E", "worker_e_result")


def node_parallel_join(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("parallel_join")
    worker_results = {}
    collected_commands: list[str] = list(state.get("validation_commands") or [])
    for key, result_key in (
        ("WORKER_A", "worker_a_result"),
        ("WORKER_B", "worker_b_result"),
        ("WORKER_C", "worker_c_result"),
        ("WORKER_D", "worker_d_result"),
        ("WORKER_E", "worker_e_result"),
    ):
        result = state.get(result_key)
        if isinstance(result, dict):
            worker_results[key] = result
            for cmd in result.get("commands") or []:
                if cmd not in collected_commands:
                    collected_commands.append(str(cmd))
    files = sum(len((r or {}).get("files_written", [])) for r in worker_results.values())
    errors_by_worker = {k: r.get("errors") or [] for k, r in worker_results.items() if r.get("errors")}
    all_errors = [f"{k}: {e}" for k, errs in errors_by_worker.items() for e in errs]
    ws.update_workflow_node_status("parallel_join", "done", f"{len(worker_results)} workers, {files} files")
    return {
        "worker_results": worker_results,
        "worker_result": {"files_written": files, "workers": worker_results, "errors": all_errors},
        "validation_commands": collected_commands[:12],
    }


def node_restore_worker(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("restore_worker")
    ws.update_workflow_node_status("restore_worker", "running", "Restoring backup")
    workflow_event("restore_worker", "restore_enter", "fast_path restore")
    ws.set_pipeline_status_message("Worker dang khoi phuc backup...")
    try:
        from core.storage.code_backup import restore_backup, rollback_task, search_backups

        project_root = state.get("project_root", "")
        brief = brief_from_state(state)
        task_uuid = str(getattr(brief, "task_uuid", "") or state.get("task_uuid") or "")
        if task_uuid:
            # Prefer task-uuid rollback (restores all files for the task atomically)
            restored_count = rollback_task(task_uuid, project_root)
            result = {"restored": restored_count, "task_uuid": task_uuid}
        else:
            # Fallback: text search scoped to project_root only; never scan full DB
            query = str(state.get("task") or state.get("original_prompt") or "")
            if not query and not project_root:
                result = {"restored": 0, "error": "no backup found: need task_uuid or query with project_root"}
            else:
                hits = search_backups(query, limit=1, project_root=project_root)
                if not hits:
                    result = {"restored": 0, "error": "no backup found"}
                else:
                    item = hits[0]
                    restored = restore_backup(int(item["id"]), project_root)
                    result = {"restored": 1, **restored}
    except Exception as exc:
        result = {"restored": 0, "error": str(exc)}
    ws.update_workflow_node_status("restore_worker", "done", f"restored={result.get('restored', 0)}")
    workflow_event("restore_worker", "restore_done", str(result)[:300])
    ws.set_pipeline_status_message(f"Restore xong: {result.get('restored', 0)} file")
    return {"restore_result": result, "worker_result": result}


def node_secretary(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("secretary")
    ws.update_workflow_node_status("secretary", "running", "Running validation commands")
    workflow_event("secretary", "enter", "Secretary running commands")
    ws.set_pipeline_status_message("Secretary dang chay validation commands...")
    ctx = state.get("context_path")
    tools = state.get("tools_path")
    project_root = state.get("project_root", "")
    if not ctx:
        workflow_event("secretary", "secretary_skipped", "no context_path")
        ws.update_workflow_node_status("secretary", "done", "skipped")
        return {"secretary_result": None}
    commands = list(state.get("validation_commands") or [])
    result = secretary_execute_commands(ctx, tools, project_root, commands=commands or None)
    cmds_run = result.get("commands_run", [])
    passed = sum(1 for c in cmds_run if c.get("success"))
    ws.update_workflow_node_status("secretary", "done", f"{passed}/{len(cmds_run)} passed")
    workflow_event("secretary", "secretary_done", f"commands={len(cmds_run)} passed={passed}")
    ws.set_pipeline_status_message(f"Secretary xong: {passed}/{len(cmds_run)} commands passed")
    return {"secretary_result": result}


def node_finalize_phase1(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("finalize_phase1")
    ws.update_workflow_node_status("finalize_phase1", "running", "Finalize")
    should_finalize = ws.consume_should_finalize()
    if should_finalize:
        workflow_event("finalize_phase1", "enter", "finalize")
        ws.set_pipeline_status_message("Finalize phase 1...")
    else:
        workflow_event("finalize_phase1", "skip_finalize_not_accepted", "context not accepted yet")
        ws.set_pipeline_status_message("Skip finalize: cho context accept")
    ctx = state.get("context_path")
    if not ctx:
        return {}
    path = Path(ctx)
    if should_finalize:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        brief = brief_from_state(state)
        update_context_state("completed", path, reason="workflow_completed", task_uuid=brief.task_uuid)
    return {}


def node_end_failed(state: TeamState) -> TeamState:
    _ = state
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("end_failed")
    ws.update_workflow_node_status("end_failed", "error", "Graph failed")
    workflow_event("end_failed", "terminal", "graph failed branch")
    ws.set_pipeline_status_message("Nhanh end_failed - xem log / regenerate")
    return {}


__all__ = [
    "brief_from_state",
    "node_leader_generate",
    "node_human_context_gate",
    "node_parallel_prepare",
    "node_secretary_setup",
    "node_tool_curator",
    "node_worker",
    "node_worker_a",
    "node_worker_b",
    "node_worker_c",
    "node_worker_d",
    "node_worker_e",
    "node_parallel_join",
    "node_restore_worker",
    "node_secretary",
    "node_finalize_phase1",
    "node_end_failed",
]
