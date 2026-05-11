"""Pipeline visual state management for workflow sessions.

Thin facade: stream state, stream history, role substates, clarification, and
diff state all live in focused submodules.  This module owns pipeline lifecycle
(stop signal, active_step, transitions) and re-exports everything so callers
that import from here continue to work unchanged.
"""
from __future__ import annotations

from pathlib import Path
import threading
import time
import uuid
from typing import Any

# -- Global stop signal for background pipeline thread ------------------------
_PIPELINE_STOP_EVENT: threading.Event = threading.Event()

# -- In-memory run_finished flag -----------------------------------------------
_RUN_FINISHED = threading.Event()

# -- Submodule re-exports ------------------------------------------------------
from .state import _stream_state as _ss
from .state._stream_state import (
    clear_leader_stream_buffer, append_leader_stream_chunk, drain_leader_stream_buffer,
    set_reasoning_active, is_reasoning_active,
    append_reasoning_chunk, drain_reasoning_buffer, clear_reasoning_buffer,
    increment_stream_char_count, get_stream_char_count,
    set_stream_prompt_tokens, get_stream_prompt_tokens,
    set_stream_completion_tokens, get_stream_completion_tokens,
    reset_stream_token_counters,
    set_leader_action, get_leader_action, clear_leader_action,
)


def __getattr__(name: str):
    """Forward private attribute lookups (_STREAM_BUFFER, _LEADER_STREAM_MAX, etc.) to _stream_state."""
    if hasattr(_ss, name):
        return getattr(_ss, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
from .state._stream_history import append_stream_line, get_stream_history, clear_stream_history
from .state._role_substates import (
    set_curator_substate, get_curator_substate, clear_curator_substate,
    set_ambassador_substate, get_ambassador_substate, clear_ambassador_substate,
    set_leader_substate, get_leader_substate, clear_leader_substate,
    set_worker_substate, get_worker_substate, clear_worker_substate,
    push_worker_reading_file, get_worker_reading_files, clear_worker_reading_files,
    set_worker_using_command, get_worker_using_command,
    push_worker_command_result, get_worker_command_results, clear_worker_state,
    set_secretary_substate, get_secretary_substate, clear_secretary_substate,
    push_secretary_command_result, get_secretary_command_results, clear_secretary_commands,
    set_explainer_substate, get_explainer_substate, clear_explainer_substate,
)
from .state._clarification import (
    set_clarification, is_clarification_pending, get_clarification,
    answer_clarification, get_clarification_answer, clear_clarification,
)
from .state._diff_state import push_update_diff, get_update_diffs, pop_update_diffs, clear_update_diffs
from ._session_core import (
    CONTEXT_ACCEPT_STATUSES, WORKFLOW_PHASES, load_session, save_session,
)
from .session_notification import get_pipeline_toast_text, list_active_notifications
from .session_pause_manager import is_paused_for_review, set_paused_for_review


# -- Pipeline stop control -----------------------------------------------------

def request_pipeline_stop() -> None:
    _PIPELINE_STOP_EVENT.set()


def _delete_current_run_artifacts(run_id: str | None = None) -> list[str]:
    deleted: list[str] = []
    candidates: set[Path] = set()
    s = load_session()
    for key in ("context_path", "state_json_path", "tools_path"):
        raw = s.get(key)
        if raw:
            path = Path(str(raw))
            if path.name in {"context.md", "state.json", "tools.md"}:
                candidates.add(path)
                candidates.add(path.with_name("state.json"))
                candidates.add(path.with_name("context.md"))
                candidates.add(path.with_name("tools.md"))
    rid = str(run_id or s.get("pipeline_run_id") or s.get("task_uuid") or "").strip()
    if rid:
        try:
            from utils.file_manager import paths_for_task

            task_paths = paths_for_task(rid)
            candidates.update(
                {
                    task_paths.state_path,
                    task_paths.context_path,
                    task_paths.run_dir / "tools.md",
                }
            )
        except Exception:
            pass
    for path in candidates:
        try:
            resolved = path.resolve()
            if resolved.name not in {"context.md", "state.json", "tools.md"}:
                continue
            if resolved.exists() and resolved.is_file():
                resolved.unlink()
                deleted.append(str(resolved))
        except OSError:
            continue
    return deleted


def request_pipeline_abort(
    reason: str = "aborted",
    run_id: str | None = None,
    task_uuid: str | None = None,
) -> dict[str, Any]:
    """Abort the active workflow immediately and clear transient gate state."""
    rid = run_id or task_uuid
    _PIPELINE_STOP_EVENT.set()
    deleted = _delete_current_run_artifacts(rid)
    try:
        clear_clarification()
        clear_leader_stream_buffer()
        clear_reasoning_buffer()
        reset_stream_token_counters()
        clear_leader_action()
        clear_ambassador_substate()
        clear_leader_substate()
        clear_curator_substate()
        clear_worker_state()
        clear_secretary_substate()
        clear_secretary_commands()
        clear_explainer_substate()
        clear_update_diffs()
        set_paused_for_review(False, None)
    except Exception:
        pass
    s = load_session()
    s["pipeline_active_step"] = "stopped"
    s["pipeline_status_message"] = "Stopped"
    s["pipeline_graph_failed"] = False
    s["pipeline_paused_at_gate"] = False
    s["pipeline_run_finished"] = True
    s["pipeline_stop_phase"] = "idle"
    s["pipeline_abort_reason"] = str(reason or "aborted")[:300]
    s["context_accept_status"] = "none"
    s["pipeline_toast"] = "Stopped"
    s["pipeline_toast_until"] = time.time() + 3.0
    s["monitor_command_queue"] = []
    for key in ("paused_for_review", "check_done", "last_node", "should_finalize", "context_path"):
        s.pop(key, None)
    save_session(s)
    _RUN_FINISHED.set()
    return {"aborted": True, "reason": str(reason or "aborted"), "deleted": deleted}


def clear_pipeline_stop() -> None:
    _PIPELINE_STOP_EVENT.clear()


def is_pipeline_stop_requested() -> bool:
    return _PIPELINE_STOP_EVENT.is_set()


# -- Pipeline visual state -----------------------------------------------------

def get_workflow_activity_min_ts() -> float:
    try:
        return float(load_session().get("workflow_activity_min_ts") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def reset_pipeline_visual() -> None:
    """Reset pipeline UI state for a new run.

    tui_stream_history is intentionally NOT cleared here — it persists across
    task resets and only clears when the user explicitly declines.
    """
    _RUN_FINISHED.clear()
    now = time.time()
    s = load_session()
    s["workflow_activity_min_ts"] = now
    s["pipeline_active_step"] = "idle"
    s["pipeline_ambassador_status"] = "idle"
    s.pop("pipeline_brief_tier", None)
    s.pop("pipeline_brief_selected_leader", None)
    s["pipeline_graph_failed"] = False
    s["pipeline_paused_at_gate"] = False
    s["pipeline_run_finished"] = False
    s["pipeline_stop_phase"] = "idle"
    s["pipeline_redirect"] = None
    s["monitor_command_queue"] = []
    s["pipeline_active_step_updated_at"] = 0.0
    s["pipeline_busy_ts"] = 0.0
    s["pipeline_status_message"] = ""
    s["pipeline_toast"] = ""
    s["pipeline_toast_until"] = 0.0
    s["pipeline_toast_queue"] = []
    s["context_accept_status"] = "none"
    s["pipeline_notifications"] = []
    s["dismissed_notification_ids"] = []
    s["workflow_list_nodes_state"] = []
    s["workflow_list_timeline"] = []
    save_session(s)
    clear_leader_stream_buffer()
    clear_reasoning_buffer()
    reset_stream_token_counters()
    clear_leader_action()
    clear_ambassador_substate()
    clear_leader_substate()


def apply_stale_workflow_ui_if_needed(project_root: str) -> None:
    from core.cli.python_cli.features.context.flow import find_context_md, is_no_context

    ctx = find_context_md(project_root)
    ctx_ok = ctx is not None and not is_no_context(ctx)
    if not ctx_ok:
        s0 = load_session()
        if is_paused_for_review() or bool(s0.get("pipeline_paused_at_gate")):
            set_paused_for_review(False, None)
            s0["pipeline_paused_at_gate"] = False
            s0["context_accept_status"] = "none"
            s0["pipeline_active_step"] = "idle"
            s0["pipeline_status_message"] = ""
            save_session(s0)
    if ctx_ok:
        return
    s = load_session()
    q = s.get("monitor_command_queue")
    if isinstance(q, list) and len(q) > 0:
        return
    if str(s.get("pipeline_ambassador_status") or "") == "running":
        return
    if str(s.get("pipeline_active_step") or "idle") != "idle":
        return
    s["workflow_activity_min_ts"] = time.time()
    s["pipeline_active_step"] = "idle"
    s["pipeline_ambassador_status"] = "idle"
    s.pop("pipeline_brief_tier", None)
    s.pop("pipeline_brief_selected_leader", None)
    s["pipeline_graph_failed"] = False
    s["pipeline_run_finished"] = False
    s["pipeline_paused_at_gate"] = False
    s["pipeline_stop_phase"] = "idle"
    s["workflow_list_nodes_state"] = []
    s["pipeline_status_message"] = ""
    s["context_accept_status"] = "none"
    save_session(s)
    clear_leader_stream_buffer()


# -- Session-backed pipeline state getters/setters -----------------------------

def set_workflow_project_root(root: str | None) -> None:
    s = load_session()
    if root:
        s["workflow_project_root"] = root
    else:
        s.pop("workflow_project_root", None)
    save_session(s)


def get_workflow_project_root() -> str | None:
    r = load_session().get("workflow_project_root")
    return str(r) if r else None


def set_pipeline_status_message(msg: str) -> None:
    s = load_session()
    s["pipeline_status_message"] = str(msg)[:500]
    save_session(s)


def get_pipeline_status_message() -> str:
    return str(load_session().get("pipeline_status_message") or "")


def set_pipeline_redirect(target: str | None) -> None:
    s = load_session()
    s["pipeline_redirect"] = target
    save_session(s)


def get_pipeline_redirect() -> str | None:
    return load_session().get("pipeline_redirect")


def set_context_accept_status(status: str) -> None:
    status = str(status or "none").lower()
    if status not in CONTEXT_ACCEPT_STATUSES:
        status = "none"
    s = load_session()
    s["context_accept_status"] = status
    save_session(s)


def get_context_accept_status() -> str:
    status = str(load_session().get("context_accept_status") or "none").lower()
    return status if status in CONTEXT_ACCEPT_STATUSES else "none"


def set_workflow_last_view_mode(mode: str) -> None:
    s = load_session()
    s["workflow_last_view_mode"] = "list" if str(mode).lower() == "list" else "chain"
    save_session(s)


def get_workflow_last_view_mode() -> str:
    m = str(load_session().get("workflow_last_view_mode") or "chain").lower()
    return "list" if m == "list" else "chain"


def set_workflow_list_nodes_state(items: list[dict[str, Any]]) -> None:
    s = load_session()
    s["workflow_list_nodes_state"] = list(items or [])[:30]
    save_session(s)


def get_workflow_list_nodes_state() -> list[dict[str, Any]]:
    raw = load_session().get("workflow_list_nodes_state")
    return list(raw) if isinstance(raw, list) else []


def append_workflow_list_event(event: dict[str, Any]) -> None:
    s = load_session()
    arr = s.get("workflow_list_timeline")
    if not isinstance(arr, list):
        arr = []
    rec = dict(event or {})
    rec["ts"] = float(rec.get("ts") or time.time())
    arr.append(rec)
    s["workflow_list_timeline"] = arr[-300:]
    save_session(s)


def get_workflow_list_timeline(limit: int = 200) -> list[dict[str, Any]]:
    raw = load_session().get("workflow_list_timeline")
    if not isinstance(raw, list):
        return []
    return list(raw[-max(1, int(limit)):])


def update_workflow_node_status(node: str, status: str, detail: str = "") -> None:
    node = str(node)
    status = str(status)
    s = load_session()
    arr = s.get("workflow_list_nodes_state")
    if not isinstance(arr, list):
        arr = []
    found = False
    for item in arr:
        if isinstance(item, dict) and str(item.get("node")) == node:
            item["status"] = status
            item["detail"] = detail[:500]
            item["updated_at"] = time.time()
            found = True
            break
    if not found:
        arr.append({"node": node, "status": status,
                    "detail": detail[:500], "updated_at": time.time()})
    s["workflow_list_nodes_state"] = arr[-30:]
    tl = s.get("workflow_list_timeline")
    if not isinstance(tl, list):
        tl = []
    tl.append({"ts": time.time(), "node": node, "status": status, "detail": detail[:500]})
    s["workflow_list_timeline"] = tl[-300:]
    save_session(s)


def set_pipeline_ambassador_status(status: str) -> None:
    s = load_session()
    s["pipeline_ambassador_status"] = status
    if status == "running":
        s["pipeline_active_step"] = "ambassador"
        s["pipeline_busy_ts"] = time.time()
        s["pipeline_active_step_updated_at"] = time.time()
    save_session(s)


def set_pipeline_after_ambassador(brief) -> None:
    s = load_session()
    s["pipeline_ambassador_status"] = "done"
    s["pipeline_brief_tier"] = getattr(brief, "tier", None) or "MEDIUM"
    s["pipeline_brief_selected_leader"] = getattr(brief, "selected_leader", None) or ""
    s["pipeline_active_step"] = "idle"
    s["pipeline_busy_ts"] = time.time()
    save_session(s)
    clear_leader_stream_buffer()
    clear_reasoning_buffer()


def set_pipeline_ambassador_error() -> None:
    s = load_session()
    s["pipeline_ambassador_status"] = "error"
    s["pipeline_active_step"] = "ambassador"
    save_session(s)


def touch_pipeline_busy() -> None:
    s = load_session()
    s["pipeline_busy_ts"] = time.time()
    save_session(s)


def set_pipeline_active_step(step: str) -> None:
    s = load_session()
    now = time.time()
    prev = str(s.get("pipeline_active_step") or "idle")
    s["pipeline_active_step"] = step
    s["pipeline_active_step_updated_at"] = now
    s["pipeline_busy_ts"] = now
    if step != "human_context_gate":
        s["pipeline_paused_at_gate"] = False
    save_session(s)
    if prev != step and step in {"ambassador", "leader_generate", "tool_curator", "worker", "secretary"}:
        clear_leader_stream_buffer()
        clear_reasoning_buffer()


def set_pipeline_paused_at_gate(paused: bool) -> None:
    s = load_session()
    s["pipeline_paused_at_gate"] = paused
    if paused:
        s["pipeline_active_step"] = "human_context_gate"
    save_session(s)


def set_pipeline_graph_failed(failed: bool) -> None:
    s = load_session()
    s["pipeline_graph_failed"] = failed
    save_session(s)


def set_pipeline_run_finished(finished: bool) -> None:
    if finished:
        _RUN_FINISHED.set()
    else:
        _RUN_FINISHED.clear()
    s = load_session()
    s["pipeline_run_finished"] = finished
    if finished:
        s["pipeline_active_step"] = "idle"
    save_session(s)


def get_pipeline_stop_phase() -> str:
    return str(load_session().get("pipeline_stop_phase") or "idle")


def set_pipeline_stop_phase(phase: str) -> None:
    phase = str(phase or "idle").lower()
    if phase not in WORKFLOW_PHASES:
        phase = "idle"
    s = load_session()
    s["pipeline_stop_phase"] = phase
    save_session(s)


def set_phase_running() -> None:
    set_pipeline_stop_phase("running")


def set_phase_paused_gate() -> None:
    set_pipeline_stop_phase("paused_gate")


def transition_pipeline_begin_run() -> None:
    _RUN_FINISHED.clear()
    s = load_session()
    s["pipeline_run_finished"] = False
    s["pipeline_paused_at_gate"] = False
    s["pipeline_graph_failed"] = False
    s["pipeline_busy_ts"] = time.time()
    save_session(s)


def set_pipeline_run_id(run_id: str | None) -> None:
    s = load_session()
    if run_id:
        s["pipeline_run_id"] = str(run_id)
    else:
        s.pop("pipeline_run_id", None)
    save_session(s)


def transition_pipeline_active(step: str) -> None:
    set_pipeline_active_step(step)


def transition_pipeline_finish(*, failed: bool = False) -> None:
    _RUN_FINISHED.set()
    s = load_session()
    s["pipeline_run_finished"] = True
    s["pipeline_graph_failed"] = bool(failed)
    s["pipeline_active_step"] = "idle"
    save_session(s)


def transition_pipeline_pause_at_gate() -> None:
    s = load_session()
    s["pipeline_paused_at_gate"] = True
    s["pipeline_active_step"] = "human_context_gate"
    save_session(s)


def enqueue_monitor_command(action: str, payload: dict[str, Any] | None = None) -> None:
    s = load_session()
    q = s.get("monitor_command_queue")
    if not isinstance(q, list):
        q = []
    q.append({"id": str(uuid.uuid4()), "action": action, "payload": dict(payload or {})})
    s["monitor_command_queue"] = q
    save_session(s)


def drain_monitor_command_queue() -> list[dict[str, Any]]:
    s = load_session()
    q = s.get("monitor_command_queue")
    s["monitor_command_queue"] = []
    save_session(s)
    if not isinstance(q, list):
        return []
    return list(q)


def get_pipeline_snapshot() -> dict[str, Any]:
    s = load_session()
    return {
        "active_step":               s.get("pipeline_active_step") or "idle",
        "ambassador_status":         s.get("pipeline_ambassador_status") or "idle",
        "brief_tier":                s.get("pipeline_brief_tier"),
        "brief_selected_leader":     str(s.get("pipeline_brief_selected_leader") or ""),
        "graph_failed":              bool(s.get("pipeline_graph_failed")),
        "paused_at_gate":            bool(s.get("pipeline_paused_at_gate")),
        "run_finished":              _RUN_FINISHED.is_set(),
        "stop_phase":                str(s.get("pipeline_stop_phase") or "idle"),
        "active_step_updated_at":    float(s.get("pipeline_active_step_updated_at") or 0.0),
        "busy_ts":                   float(s.get("pipeline_busy_ts") or 0.0),
        "status_message":            str(s.get("pipeline_status_message") or ""),
        "toast":                     get_pipeline_toast_text(),
        "context_accept_status":     str(s.get("context_accept_status") or "none"),
        "leader_stream_buffer":      _ss._STREAM_BUFFER,
        "leader_stream_updated_at":  _ss._STREAM_UPDATED_AT,
        "notifications":             list_active_notifications(),
        "workflow_last_view_mode":   str(s.get("workflow_last_view_mode") or "chain"),
        "workflow_list_nodes_state": list(get_workflow_list_nodes_state()),
        "workflow_list_timeline":    list(get_workflow_list_timeline(120)),
    }
