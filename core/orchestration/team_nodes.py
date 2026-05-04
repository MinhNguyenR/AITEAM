from __future__ import annotations

import logging
from pathlib import Path

from core.app_state.context_state import update_context_state
from core.runtime import session as ws
from core.domain.delta_brief import DeltaBrief
from utils.file_manager import paths_for_task
from utils.logger import artifact_detail, workflow_event

from .pipeline_artifacts import (
    leader_generate_context,
    tool_curator_generate_tools,
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
    "node_tool_curator",
    "node_finalize_phase1",
    "node_end_failed",
]
