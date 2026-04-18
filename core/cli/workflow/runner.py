"""LangGraph workflow runner: stream, resume, rewind; Rich Live when inline_progress."""

from __future__ import annotations

import logging
import subprocess
import sys
import time
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
from typing import Literal

from rich.box import ROUNDED
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from agents.teamMap._team_map import get_graph
from core.cli.state import log_system_action, update_context_state
from core.cli.workflow import session as ws
from core.cli.workflow.activity_log import list_recent_activity, truncate_workflow_activity_from_ts
from core.cli.workflow.checkpointer import get_checkpointer
from core.cli.ui import console
from utils.file_manager import paths_for_task
from utils.logger import artifact_detail, workflow_event

logger = logging.getLogger(__name__)
AI_TEAM_ROOT = Path(__file__).resolve().parents[3]

RunOutcome = Literal["paused", "completed", "failed"]


def _normalize_stream_node_key(key: object) -> str:
    if isinstance(key, tuple):
        return str(key[-1]) if key else ""
    return str(key)


def _task_workspace_from_values(values: dict) -> tuple[str, Path] | tuple[None, None]:
    brief_dict = values.get("brief_dict")
    if not isinstance(brief_dict, dict):
        return None, None
    task_uuid = str(brief_dict.get("task_uuid") or "").strip()
    if not task_uuid:
        return None, None
    ws_paths = paths_for_task(task_uuid)
    return task_uuid, ws_paths.run_dir


def _truncate_log_tail_from(ts_start: float) -> None:
    truncate_workflow_activity_from_ts(ts_start)


def _history_ts(obj: object) -> float:
    if isinstance(obj, (int, float)):
        return float(obj)
    if isinstance(obj, str):
        raw = obj.strip()
        if not raw:
            return time.time()
        try:
            return float(raw)
        except ValueError:
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00")).timestamp()
            except ValueError:
                return time.time()
    return time.time()


def _cleanup_artifacts_from_target(values: dict, target_node: str, ts_start: float) -> None:
    task_id, run_dir = _task_workspace_from_values(values)
    if not task_id or run_dir is None:
        return
    files_by_node: dict[str, list[str]] = {
        "leader_generate": ["state.json", "context.md"],
        "expert_solo": ["state.json", "context.md"],
        "expert_coplan": ["validation_report.md", "context.md"],
        "human_context_gate": ["context.md"],
        "finalize_phase1": ["context.md", "state.json", "validation_report.md"],
    }
    chain = ["leader_generate", "expert_solo", "expert_coplan", "human_context_gate", "finalize_phase1"]
    if target_node not in chain:
        target_node = "leader_generate"
    start_idx = chain.index(target_node)
    for node in chain[start_idx:]:
        for filename in files_by_node.get(node, []):
            p = run_dir / filename
            if p.exists():
                try:
                    p.unlink(missing_ok=True)
                    workflow_event(node, "artifact_deleted_on_rewind", artifact_detail(p, task_id=task_id, producer_node=node))
                except OSError:
                    pass
    _truncate_log_tail_from(ts_start)


def spawn_workflow_monitor(view_mode: str = "chain") -> bool:
    mode = "list" if str(view_mode).lower() == "list" else "chain"
    cmd = [sys.executable, "-m", "core.cli.workflow.monitor", "--view", mode]
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


def _inline_badge(status: str) -> str:
    st = str(status or "pending").lower()
    return {
        "pending": "[dim]PENDING[/dim]",
        "running": "[yellow]RUNNING[/yellow]",
        "complete": "[green]COMPLETE[/green]",
        "error": "[red]ERROR[/red]",
    }.get(st, "[dim]PENDING[/dim]")


def _chain_step_labels() -> dict[str, str]:
    return {
        "ambassador": "Amb",
        "leader_generate": "Leader",
        "expert_solo": "Expert",
        "expert_coplan": "CoPlan",
        "human_context_gate": "Review",
        "finalize_phase1": "Done",
        "end_failed": "Fail",
    }


def _inline_workflow_renderable(tier: str, status_message: str = "", *, ui_style: str = "list"):
    nodes = ws.get_workflow_list_nodes_state()
    style = "chain" if str(ui_style).lower() == "chain" else "list"
    subtitle = status_message[:120] if status_message else "Dang chay pipeline..."
    if style == "chain":
        labels = _chain_step_labels()
        chunks: list[str] = []
        for item in nodes:
            node = str(item.get("node", ""))
            st = str(item.get("status", "pending")).lower()
            short = labels.get(node, node[:8])
            if st == "complete":
                sym = f"[green]{short}[/green]"
            elif st == "running":
                sym = f"[yellow bold]{short}[/yellow bold]"
            elif st == "error":
                sym = f"[red]{short}[/red]"
            else:
                sym = f"[dim]{short}[/dim]"
            chunks.append(sym)
        body = Text.from_markup(" [dim]→[/dim] ".join(chunks) if chunks else "[dim]…[/dim]")
        return Panel(
            body,
            title=f"Workflow (chain) | tier={tier}",
            subtitle=subtitle,
            border_style="cyan",
            box=ROUNDED,
        )
    table = Table(box=ROUNDED, border_style="cyan", expand=True)
    table.add_column("#", width=3, style="dim")
    table.add_column("Node", width=24)
    table.add_column("Status", width=12)
    table.add_column("Detail")
    for idx, item in enumerate(nodes, 1):
        node = str(item.get("node", ""))
        detail = str(item.get("detail", "") or "")
        if len(detail) > 80:
            detail = detail[:77] + "..."
        table.add_row(str(idx), node, _inline_badge(str(item.get("status", "pending"))), detail)
    return Panel(table, title=f"Workflow (list) | tier={tier}", subtitle=subtitle, border_style="cyan", box=ROUNDED)


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
                    _inline_workflow_renderable(tier, ws.get_pipeline_status_message() or "", ui_style=ui_style),
                    console=console,
                    refresh_per_second=6,
                    transient=True,
                )
            )
        try:
            for event in graph.stream(init, config):
                for node_name in event:
                    name = _normalize_stream_node_key(node_name)
                    if not name or name.startswith("__"):
                        continue
                    ws.set_last_node(name)
                    ws.set_pipeline_active_step(name)
                    ws.update_workflow_node_status(name, "complete", "stream tick")
                    workflow_event(name, "node_complete", "stream tick")
                    ws.set_pipeline_status_message(f"Da chay xong node: {name}")
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
                            _inline_workflow_renderable(
                                tier,
                                ws.get_pipeline_status_message() or "",
                                ui_style=ui_style,
                            )
                        )
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


def resume_workflow() -> bool:
    tid = ws.get_thread_id()
    if not tid or not ws.is_paused_for_review():
        return False
    ws.set_phase_running()
    ws.set_pipeline_paused_at_gate(False)
    ws.set_pipeline_active_step("human_context_gate")

    ib = ws.get_interrupt_before()
    graph = get_graph(get_checkpointer(), interrupt_before=ib)
    config = {"configurable": {"thread_id": tid}}
    try:
        while True:
            graph.invoke(None, config)
            snap = graph.get_state(config)
            if not snap.next:
                break
    except (RuntimeError, ValueError, OSError, KeyError, TypeError):
        logger.exception("workflow resume failed")
        return False

    ws.set_paused_for_review(False)
    ws.set_last_node(None)
    ws.set_pipeline_run_finished(True)
    ws.set_pipeline_active_step("idle")
    ws.set_pipeline_stop_phase("idle")
    if ws.get_context_accept_status() not in {"accepted", "deferred"}:
        ws.set_context_accept_status("none")
    return True


def rewind_current() -> bool:
    workflow_event("runner", "rewind_current", "resume current checkpoint")
    return resume_workflow()


def _stream_from_values(values: dict, *, interrupt_before: tuple[str, ...]) -> bool:
    graph = get_graph(get_checkpointer(), interrupt_before=interrupt_before)
    tid = ws.new_thread_id()
    cfg = {"configurable": {"thread_id": tid}}
    ws.set_interrupt_before(list(interrupt_before))
    ws.set_pipeline_graph_failed(False)
    ws.set_pipeline_run_finished(False)
    ws.set_phase_running()
    ws.set_context_accept_status("none")
    try:
        for event in graph.stream(values, cfg):
            for node_name in event:
                name = _normalize_stream_node_key(node_name)
                if not name or name.startswith("__"):
                    continue
                ws.set_last_node(name)
                ws.set_pipeline_active_step(name)
                ws.update_workflow_node_status(name, "complete", "rewind stream tick")
                workflow_event(name, "node_complete", "rewind stream tick")
        snap = graph.get_state(cfg)
        vals = (snap.values or {}) if snap else {}
        ctx = vals.get("context_path")
        if vals.get("leader_failed") or not ctx:
            ws.set_pipeline_graph_failed(True)
            ws.set_pipeline_status_message("Rewind that bai (leader/context)")
            workflow_event("runner", "rewind_failed", "leader_failed hoac thieu context_path")
            return False
        if snap and snap.next:
            ws.set_paused_for_review(True, str(ctx))
            ws.set_pipeline_paused_at_gate(True)
            ws.set_phase_paused_gate()
            ws.set_context_accept_status("pending")
            task_id, _ = _task_workspace_from_values(vals)
            workflow_event(
                "human_context_gate",
                "paused_review",
                artifact_detail(ctx, task_id=task_id or "", producer_node="human_context_gate"),
            )
            return True
        ws.set_pipeline_run_finished(True)
        ws.set_pipeline_stop_phase("idle")
        task_id, _ = _task_workspace_from_values(vals)
        if ctx:
            workflow_event("runner", "rewind_completed", artifact_detail(ctx, task_id=task_id or "", producer_node="runner"))
        else:
            workflow_event("runner", "rewind_completed", "status=done")
        return True
    except (RuntimeError, ValueError, OSError, KeyError, TypeError):
        logger.exception("rewind stream failed")
        ws.set_pipeline_graph_failed(True)
        workflow_event("runner", "rewind_failed", "exception during rewind stream")
        return False


def rewind_to_checkpoint(target: int | str) -> bool:
    tid = ws.get_thread_id()
    if not tid:
        return False
    ib = ws.get_interrupt_before()
    graph = get_graph(get_checkpointer(), interrupt_before=ib)
    cfg = {"configurable": {"thread_id": tid}}
    try:
        hist = list(graph.get_state_history(cfg))
    except (OSError, ValueError, KeyError, TypeError):
        logger.exception("failed to read state history for rewind")
        return False
    if not hist:
        return False
    chosen = None
    if isinstance(target, int):
        if 0 <= target < len(hist):
            chosen = hist[target]
    else:
        t = str(target).strip().lower()
        for h in hist:
            vals = getattr(h, "values", None) or {}
            ln = str(vals.get("last_node") or "").lower()
            if ln == t:
                chosen = h
                break
    if chosen is None:
        return False
    chosen_ts = _history_ts(getattr(chosen, "created_at", None) or getattr(chosen, "ts", None) or 0.0)
    vals = dict(getattr(chosen, "values", None) or {})
    required = {"task", "project_root", "original_prompt", "brief_dict"}
    if not required.issubset(set(vals.keys())):
        return False
    workflow_event("runner", "rewind_to_checkpoint", f"target={target}")
    target_node = str(vals.get("last_node") or "")
    _cleanup_artifacts_from_target(vals, target_node, chosen_ts)
    return _stream_from_values(vals, interrupt_before=ib)


def rewind_to_last_gate() -> bool:
    tid = ws.get_thread_id()
    if not tid:
        return False
    ib = ws.get_interrupt_before()
    graph = get_graph(get_checkpointer(), interrupt_before=ib)
    cfg = {"configurable": {"thread_id": tid}}
    try:
        hist = list(graph.get_state_history(cfg))
    except (OSError, ValueError, KeyError, TypeError):
        logger.exception("failed to read state history for gate rewind")
        return False
    if not hist:
        return False
    chosen = None
    chosen_ts = 0.0
    for h in hist:
        vals = dict(getattr(h, "values", None) or {})
        if vals.get("context_path"):
            chosen = vals
            chosen_ts = _history_ts(getattr(h, "created_at", None) or getattr(h, "ts", None) or 0.0)
            break
    if chosen is None:
        chosen = dict(getattr(hist[-1], "values", None) or {})
        chosen_ts = _history_ts(getattr(hist[-1], "created_at", None) or getattr(hist[-1], "ts", None) or 0.0)
    required = {"task", "project_root", "original_prompt", "brief_dict"}
    if not required.issubset(set(chosen.keys())):
        return False
    workflow_event("runner", "rewind_to_last_gate", "replay from last context-bearing checkpoint")
    _cleanup_artifacts_from_target(chosen, "human_context_gate", chosen_ts)
    return _stream_from_values(chosen, interrupt_before=ib)


__all__ = [
    "run_agent_graph",
    "resume_workflow",
    "RunOutcome",
    "rewind_current",
    "rewind_to_last_gate",
    "rewind_to_checkpoint",
    "spawn_workflow_monitor",
]
