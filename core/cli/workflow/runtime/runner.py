"""LangGraph workflow runner: stream, resume, rewind; Rich Live when inline_progress."""

from __future__ import annotations

import logging
import subprocess
import sys
from contextlib import ExitStack
from pathlib import Path
from typing import Literal

from rich.live import Live

from agents.team_map._team_map import get_graph
from core.bootstrap import REPO_ROOT
from core.cli.state import log_system_action, update_context_state
from core.cli.chrome.ui import console
from utils.logger import artifact_detail, workflow_event

from .activity_log import list_recent_activity
from .checkpointer import get_checkpointer
from . import session as ws
from .runner_ui import inline_workflow_renderable
from .runner_rewind import (
    _normalize_stream_node_key,
    _task_workspace_from_values,
    rewind_current,
    rewind_to_checkpoint,
    rewind_to_last_gate,
)
from .runner_resume import resume_workflow

logger = logging.getLogger(__name__)
AI_TEAM_ROOT = REPO_ROOT

RunOutcome = Literal["paused", "completed", "failed"]


def spawn_workflow_monitor(view_mode: str = "chain") -> bool:
    mode = "list" if str(view_mode).lower() == "list" else "chain"
    cmd = [sys.executable, "-m", "core.cli.workflow.tui", "--view", mode]
    kwargs: dict = {"cwd": str(AI_TEAM_ROOT)}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        logger.warning("Could not spawn workflow monitor: %s", exc)
        return False
    ws.set_monitor_pid(proc.pid)
    return True


def run_agent_graph(
    brief,
    prompt: str,
    project_root: str,
    settings: dict,
    *,
    inline_progress: bool = False,
) -> RunOutcome:
    mode = str(settings.get("workflow_view_mode") or "chain").lower()
    ws.set_workflow_last_view_mode("list" if mode == "list" else "chain")
    ws.set_workflow_project_root(project_root)
    ws.clear_leader_stream_buffer()
    tier = str(getattr(brief, "tier", "MEDIUM") or "MEDIUM")
    if tier == "LOW":
        nodes = ["ambassador", "leader_generate", "human_context_gate", "finalize_phase1"]
    elif tier == "EXPERT":
        nodes = ["ambassador", "expert_solo", "human_context_gate", "finalize_phase1"]
    elif tier == "HARD":
        nodes = ["ambassador", "leader_generate", "expert_coplan", "human_context_gate", "finalize_phase1"]
    else:
        nodes = ["ambassador", "leader_generate", "human_context_gate", "finalize_phase1"]
    ws.set_workflow_list_nodes_state(
        [{"node": n, "status": "pending", "detail": "", "updated_at": 0.0} for n in nodes]
    )
    ws.update_workflow_node_status("ambassador", "complete", f"tier={tier}")
    workflow_event("runner", "graph_start", f"project_root={project_root}")
    ws.set_pipeline_status_message("Dang chay LangGraph pipeline...")
    ws.set_phase_running()
    ws.set_context_accept_status("none")

    tid = ws.new_thread_id()
    auto = bool(settings.get("auto_accept_context"))
    ib: tuple[str, ...] = () if auto else ("human_context_gate",)
    ws.set_interrupt_before(list(ib))
    ws.set_should_finalize(auto)
    ws.set_pipeline_graph_failed(False)
    ws.set_pipeline_run_finished(False)
    ws.set_pipeline_paused_at_gate(False)

    cp = get_checkpointer()
    graph = get_graph(cp, interrupt_before=ib)
    config = {"configurable": {"thread_id": tid}}
    init = {
        "task": prompt,
        "project_root": project_root,
        "original_prompt": prompt,
        "brief_dict": brief.model_dump(),
    }

    ws.set_paused_for_review(False)
    ws.set_last_node(None)
    ws.touch_pipeline_busy()

    first_real_node = "expert_solo" if tier == "EXPERT" else "leader_generate"
    ws.set_pipeline_active_step(first_real_node)
    ws.update_workflow_node_status(first_real_node, "running", "starting")

    ui_style = str(settings.get("workflow_view_mode") or "chain")
    with ExitStack() as stack:
        live = None
        if inline_progress:
            live = stack.enter_context(
                Live(
                    inline_workflow_renderable(tier, ws.get_pipeline_status_message() or "", ui_style=ui_style),
                    console=console,
                    refresh_per_second=6,
                    transient=False,
                )
            )
        stream_seen: set[str] = set()
        try:
            for event in graph.stream(init, config):
                for node_name in event:
                    name = _normalize_stream_node_key(node_name)
                    if not name or name.startswith("__"):
                        continue
                    if name in stream_seen:
                        if live is not None:
                            live.update(
                                inline_workflow_renderable(
                                    tier,
                                    ws.get_pipeline_status_message() or "",
                                    ui_style=ui_style,
                                )
                            )
                        continue
                    stream_seen.add(name)
                    ws.set_last_node(name)
                    ws.set_pipeline_active_step(name)
                    ws.update_workflow_node_status(name, "complete", "done")
                    workflow_event(name, "node_complete", "done")
                    ws.set_pipeline_status_message(f"Da chay xong node: {name}")
                    ws.set_pipeline_toast(f"Đã chạy xong: {name}", seconds=3.0)
                    current_nodes = ws.get_workflow_list_nodes_state()
                    node_order = [str(item.get("node", "")) for item in current_nodes]
                    try:
                        idx = node_order.index(name)
                    except ValueError:
                        idx = -1
                    if idx >= 0 and idx + 1 < len(node_order):
                        next_node = node_order[idx + 1]
                        if str(next_node).lower() != "finalize_phase1":
                            ws.update_workflow_node_status(next_node, "running", "processing")
                    if live is not None:
                        live.update(
                            inline_workflow_renderable(
                                tier,
                                ws.get_pipeline_status_message() or "",
                                ui_style=ui_style,
                            )
                        )
        except KeyboardInterrupt:
            ws.set_pipeline_graph_failed(True)
            ws.update_workflow_node_status("runner", "error", "interrupted")
            workflow_event("runner", "interrupted", "KeyboardInterrupt")
            ws.set_pipeline_status_message("Dung pipeline (Ctrl+C)")
            return "failed"
        except (RuntimeError, ValueError, OSError, KeyError, TypeError):
            logger.exception("graph.stream failed")
            ws.set_pipeline_graph_failed(True)
            ws.update_workflow_node_status("runner", "error", "graph.stream failed")
            workflow_event("runner", "graph_error", "graph.stream failed")
            ws.set_pipeline_status_message("Loi pipeline - xem CLI log")
            return "failed"

        snap = graph.get_state(config)
        vals = (snap.values or {}) if snap else {}
        ctx = vals.get("context_path")
        if snap.next:
            if ctx:
                update_context_state("active", Path(ctx), reason="generated", task_uuid=getattr(brief, "task_uuid", ""))
                ws.set_paused_for_review(True, str(ctx))
                ws.push_pipeline_notification(
                    "context.md san sang",
                    f"Duong dan: {ctx}\nGo [bold]check[/bold] de review.",
                    "context_ready",
                    {"context_path": str(ctx)},
                )
            else:
                ws.set_paused_for_review(True, None)
            ws.set_pipeline_paused_at_gate(True)
            ws.set_phase_paused_gate()
            ws.set_context_accept_status("pending")
            ws.update_workflow_node_status("human_context_gate", "running", "paused for review")
            log_system_action("workflow.graph", "outcome=paused")
            workflow_event(
                "human_context_gate",
                "paused_review",
                artifact_detail(ctx, task_id=getattr(brief, "task_uuid", ""), producer_node="human_context_gate") if ctx else "paused without context.md",
            )
            ws.set_pipeline_status_message("Cho review human_context_gate")
            return "paused"

        if vals.get("leader_failed") or (not ctx and tier != "LOW"):
            ws.set_pipeline_graph_failed(True)
            ws.update_workflow_node_status("runner", "error", "leader_failed / missing context_path")
            log_system_action("workflow.graph", "outcome=failed")
            workflow_event("runner", "outcome_failed", "leader_failed hoac thieu context_path")
            ws.set_pipeline_status_message("Pipeline that bai (leader / context)")
            recent = list_recent_activity(limit=80, min_ts=ws.get_workflow_activity_min_ts() or None)
            has_state = any(str(r.get("action", "")) == "state_json_written" for r in recent)
            has_leader_enter = any(
                str(r.get("node", "")) == "leader_generate" and str(r.get("action", "")) == "enter"
                for r in recent
            )
            if not has_state or not has_leader_enter:
                workflow_event(
                    "runner",
                    "event_sequence_missing",
                    f"state_json_written={has_state} leader_enter={has_leader_enter}",
                    level="warning",
                )
            return "failed"

        ws.set_pipeline_run_finished(True)
        ws.set_pipeline_stop_phase("idle")
        ws.update_workflow_node_status("finalize_phase1", "complete", "pipeline completed")
        log_system_action("workflow.graph", "outcome=completed")
        if ctx:
            workflow_event("runner", "outcome_completed", artifact_detail(ctx, task_id=getattr(brief, "task_uuid", ""), producer_node="runner"))
        else:
            workflow_event("runner", "outcome_completed", "status=done")
        ws.set_pipeline_status_message("Pipeline hoan tat")
        return "completed"


__all__ = [
    "run_agent_graph",
    "resume_workflow",
    "RunOutcome",
    "rewind_current",
    "rewind_to_last_gate",
    "rewind_to_checkpoint",
    "spawn_workflow_monitor",
]
