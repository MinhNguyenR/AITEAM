"""
LangGraph team workflow aligned with core/cli/start_flow pipeline.

Entry state (post–Ambassador): task, project_root, original_prompt, brief_dict.
"""

from __future__ import annotations

import logging
from typing import Any, Optional, Sequence, TypedDict

from core.bootstrap import ensure_project_root

ensure_project_root()

from langgraph.graph import END, START, StateGraph

from core.domain.delta_brief import DeltaBrief
from agents.expert import Expert
from agents.leader import BaseLeader
from core.domain.pipeline_state import leader_generate_context, write_task_state_json
from core.cli.workflow.runtime import session as ws
from utils.file_manager import paths_for_task
from utils.logger import artifact_detail, workflow_event

logger = logging.getLogger(__name__)


class TeamState(TypedDict, total=False):
    task: str
    project_root: str
    original_prompt: str
    brief_dict: dict[str, Any]
    context_path: Optional[str]
    validation_status: Optional[str]
    state_json_path: Optional[str]
    leader_failed: bool


def _brief(state: TeamState) -> DeltaBrief:
    return DeltaBrief.model_validate(state["brief_dict"])


def route_entry(state: TeamState) -> str:
    tier = state["brief_dict"].get("tier", "MEDIUM")
    if tier == "LOW":
        return "leader_generate"
    if tier == "EXPERT":
        return "expert_solo"
    return "leader_generate"


def node_leader_generate(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("leader_generate")
    ws.update_workflow_node_status("leader_generate", "running", "Đang generate context")
    workflow_event("leader_generate", "enter", "Leader generate context.md")
    ws.set_pipeline_status_message("Leader đang generate context.md (streaming nếu bật)…")
    brief = _brief(state)
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
    ws.set_pipeline_status_message(f"Đã ghi context.md → {ctx}")
    return {"context_path": str(ctx), "leader_failed": False, "state_json_path": str(state_path)}


def route_after_leader(state: TeamState) -> str:
    if state.get("leader_failed") or not state.get("context_path"):
        return "end_failed"
    tier = state["brief_dict"].get("tier", "MEDIUM")
    if tier == "HARD":
        return "expert_coplan"
    return "human_context_gate"


def node_expert_solo(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("expert_solo")
    ws.update_workflow_node_status("expert_solo", "running", "Đang generate context")
    workflow_event("expert_solo", "enter", "Expert generate context")
    ws.set_pipeline_status_message("Expert đang generate context.md…")
    brief = _brief(state)
    state_path = paths_for_task(brief.task_uuid).state_path
    if not state_path.exists():
        state_path = write_task_state_json(
            brief,
            state["original_prompt"],
            state["project_root"],
            source_node="ambassador",
        )
    expert = Expert(budget_limit_usd=5.0)
    try:
        ctx_str = expert.generate_context(state_path, stream_to_monitor=True)
    except (OSError, RuntimeError, ValueError, TypeError, FileNotFoundError):
        logger.exception("expert_solo failed")
        workflow_event("expert_solo", "expert_generate_failed", "exception during generate_context")
        return {"context_path": None, "state_json_path": str(state_path), "leader_failed": True}
    if BaseLeader.is_no_context(ctx_str):
        workflow_event("expert_solo", "expert_generate_failed", "NO_CONTEXT sentinel")
        return {"context_path": None, "state_json_path": str(state_path), "leader_failed": True}
    return {"context_path": ctx_str, "state_json_path": str(state_path), "leader_failed": False}


def route_after_expert_solo(state: TeamState) -> str:
    if not state.get("context_path"):
        return "end_failed"
    return "human_context_gate"


def node_expert_coplan(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("expert_coplan")
    ws.update_workflow_node_status("expert_coplan", "running", "Đang validate")
    workflow_event("expert_coplan", "enter", "Expert validate plan")
    ws.set_pipeline_status_message("Expert (co-plan) đang validate…")
    ctx = state.get("context_path")
    stp = state.get("state_json_path")
    if not ctx or not stp:
        return {"validation_status": "MISSING_PATHS"}
    expert = Expert(budget_limit_usd=5.0)
    status = expert.validate_plan(draft_context_path=ctx, state_path=stp)
    return {"validation_status": status}


def node_human_context_gate(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("human_context_gate")
    ws.update_workflow_node_status("human_context_gate", "running", "Đợi review")
    workflow_event("human_context_gate", "enter", "interrupt_before gate")
    ws.set_pipeline_status_message("Tạm dừng tại human_context_gate — chờ review")
    return {}


def node_finalize_phase1(state: TeamState) -> TeamState:
    from pathlib import Path

    from core.cli.state import update_context_state

    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("finalize_phase1")
    ws.update_workflow_node_status("finalize_phase1", "running", "Finalize")
    should_finalize = ws.consume_should_finalize()
    if should_finalize:
        workflow_event("finalize_phase1", "enter", "finalize")
        ws.set_pipeline_status_message("Finalize phase 1…")
    else:
        workflow_event("finalize_phase1", "skip_finalize_not_accepted", "context not accepted yet")
        ws.set_pipeline_status_message("Skip finalize: chờ context accept")
    ctx = state.get("context_path")
    if not ctx:
        return {}
    p = Path(ctx)
    if should_finalize:
        try:
            p.unlink(missing_ok=True)
        except OSError:
            pass
        brief = _brief(state)
        update_context_state("completed", p, reason="workflow_completed", task_uuid=brief.task_uuid)
    return {}


def node_end_failed(state: TeamState) -> TeamState:
    ws.touch_pipeline_busy()
    ws.set_pipeline_active_step("end_failed")
    ws.update_workflow_node_status("end_failed", "error", "Graph failed")
    workflow_event("end_failed", "terminal", "graph failed branch")
    ws.set_pipeline_status_message("Nhánh end_failed — xem log / regenerate")
    return {}


_builder: StateGraph | None = None


def _build_graph() -> StateGraph:
    global _builder
    if _builder is not None:
        return _builder
    g = StateGraph(TeamState)
    g.add_node("leader_generate", node_leader_generate)
    g.add_node("expert_solo", node_expert_solo)
    g.add_node("expert_coplan", node_expert_coplan)
    g.add_node("human_context_gate", node_human_context_gate)
    g.add_node("finalize_phase1", node_finalize_phase1)
    g.add_node("end_failed", node_end_failed)

    g.add_conditional_edges(
        START,
        route_entry,
        {"expert_solo": "expert_solo", "leader_generate": "leader_generate", "human_context_gate": "human_context_gate"},
    )
    g.add_conditional_edges(
        "leader_generate",
        route_after_leader,
        {"expert_coplan": "expert_coplan", "human_context_gate": "human_context_gate", "end_failed": "end_failed"},
    )
    g.add_conditional_edges(
        "expert_solo",
        route_after_expert_solo,
        {"human_context_gate": "human_context_gate", "end_failed": "end_failed"},
    )
    g.add_edge("expert_coplan", "human_context_gate")
    g.add_edge("human_context_gate", "finalize_phase1")
    g.add_edge("finalize_phase1", END)
    g.add_edge("end_failed", END)
    _builder = g
    return g


def get_graph(checkpointer=None, interrupt_before: Sequence[str] | None = None):
    """
    Compile team workflow graph.

    interrupt_before: e.g. ("human_context_gate",) for manual review, or () when auto-accept.
    """
    seq = interrupt_before if interrupt_before is not None else ("human_context_gate",)
    ib_list = list(seq)
    return _build_graph().compile(checkpointer=checkpointer, interrupt_before=ib_list)


__all__ = ["TeamState", "get_graph"]
