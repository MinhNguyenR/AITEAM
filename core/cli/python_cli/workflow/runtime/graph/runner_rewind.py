"""Rewind helpers and public rewind functions for the LangGraph workflow runner."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path

from core.orchestration import get_graph
from utils.file_manager import paths_for_task
from utils.logger import artifact_detail, workflow_event

from ..persist.activity_log import truncate_workflow_activity_from_ts
from ..persist.checkpointer import get_checkpointer
from .. import session as ws
from .runner_resume import resume_workflow

logger = logging.getLogger(__name__)


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
        "human_context_gate": ["context.md"],
        "finalize_phase1": ["context.md", "state.json", "validation_report.md"],
    }
    chain = ["leader_generate", "human_context_gate", "finalize_phase1"]
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


def _stream_from_values(values: dict, *, interrupt_before: tuple[str, ...]) -> bool:
    graph = get_graph(get_checkpointer(), interrupt_before=interrupt_before)
    tid = ws.new_thread_id()
    cfg = {"configurable": {"thread_id": tid}}
    ws.set_interrupt_before(list(interrupt_before))
    ws.set_pipeline_graph_failed(False)
    ws.set_pipeline_run_finished(False)
    ws.set_phase_running()
    ws.set_context_accept_status("none")
    r_seen: set[str] = set()
    try:
        for event in graph.stream(values, cfg):
            for node_name in event:
                name = _normalize_stream_node_key(node_name)
                if not name or name.startswith("__"):
                    continue
                if name in r_seen:
                    continue
                r_seen.add(name)
                ws.set_last_node(name)
                ws.set_pipeline_active_step(name)
                ws.update_workflow_node_status(name, "complete", "rewind done")
                workflow_event(name, "node_complete", "rewind done")
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


def rewind_current() -> bool:
    workflow_event("runner", "rewind_current", "resume current checkpoint")
    return resume_workflow()


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
    "_normalize_stream_node_key",
    "_task_workspace_from_values",
    "_truncate_log_tail_from",
    "_history_ts",
    "_cleanup_artifacts_from_target",
    "_stream_from_values",
    "rewind_current",
    "rewind_to_checkpoint",
    "rewind_to_last_gate",
]
