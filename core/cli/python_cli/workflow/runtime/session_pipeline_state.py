"""Pipeline visual state management for workflow sessions."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any

# ── Global stop signal for background pipeline thread ────────────────────────
_PIPELINE_STOP_EVENT: threading.Event = threading.Event()

# ── In-memory leader stream buffer (avoids disk I/O per token) ───────────────
_STREAM_LOCK = threading.Lock()
_STREAM_BUFFER: str = ""
_STREAM_UPDATED_AT: float = 0.0
_LEADER_STREAM_MAX = 48_000

# ── In-memory run_finished flag (eliminates file I/O race with bg thread) ────
_RUN_FINISHED = threading.Event()  # set = finished, clear = running/idle


def request_pipeline_stop() -> None:
    """Signal the background runner thread to stop after current node."""
    _PIPELINE_STOP_EVENT.set()


def clear_pipeline_stop() -> None:
    """Clear the stop signal (called before starting a new pipeline run)."""
    _PIPELINE_STOP_EVENT.clear()


def is_pipeline_stop_requested() -> bool:
    """Return True if the TUI has requested the pipeline to stop."""
    return _PIPELINE_STOP_EVENT.is_set()


from ._session_core import (
    CONTEXT_ACCEPT_STATUSES,
    WORKFLOW_PHASES,
    load_session,
    save_session,
)
from .session_notification import (
    get_pipeline_toast_text,
    list_active_notifications,
    set_pipeline_toast,
)
from .session_pause_manager import is_paused_for_review, set_paused_for_review


# ── TUI stream history persistence ───────────────────────────────────────────
# Persists RichLog lines across TUI sessions so re-entering workflow shows
# the same stream history. Only cleared when user declines context regeneration.

_STREAM_HISTORY_MAX = 1000  # max lines stored (prevents unbounded growth)


def append_stream_line(line: str) -> None:
    """Append a Rich-markup line to the persistent TUI stream history.

    Called every time something is written to #stream_panel.
    Does NOT get cleared by reset_pipeline_visual() — survives task resets.
    """
    s = load_session()
    hist = s.get("tui_stream_history")
    if not isinstance(hist, list):
        hist = []
    hist.append(str(line))
    if len(hist) > _STREAM_HISTORY_MAX:
        hist = hist[-_STREAM_HISTORY_MAX:]
    s["tui_stream_history"] = hist
    save_session(s)


def get_stream_history() -> list[str]:
    """Return all persisted TUI stream lines (for replaying on TUI mount)."""
    raw = load_session().get("tui_stream_history")
    if not isinstance(raw, list):
        return []
    return [str(x) for x in raw]


def clear_stream_history() -> None:
    """Clear stream history. Only called when user declines y/n after delete.

    The backend activity log (workflow_activity.log) is NEVER touched here —
    that always keeps the full audit trail.
    """
    s = load_session()
    s["tui_stream_history"] = []
    save_session(s)


# ── Pipeline visual state ─────────────────────────────────────────────────────

def get_workflow_activity_min_ts() -> float:
    try:
        return float(load_session().get("workflow_activity_min_ts") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def reset_pipeline_visual() -> None:
    """Reset pipeline UI state for a new run.

    NOTE: tui_stream_history is intentionally NOT cleared here.
    Stream history persists across task resets; it only clears on user decline.
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
    # tui_stream_history intentionally preserved
    save_session(s)
    clear_leader_stream_buffer()


def apply_stale_workflow_ui_if_needed(project_root: str) -> None:
    if _RUN_FINISHED.is_set():
        return  # pipeline just finished; let TUI tick handle it before resetting
    from core.cli.python_cli.flows.context_flow import find_context_md, is_no_context

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


def clear_leader_stream_buffer() -> None:
    global _STREAM_BUFFER, _STREAM_UPDATED_AT
    with _STREAM_LOCK:
        _STREAM_BUFFER = ""
        _STREAM_UPDATED_AT = 0.0


def append_leader_stream_chunk(text: str) -> None:
    global _STREAM_BUFFER, _STREAM_UPDATED_AT
    if not text:
        return
    with _STREAM_LOCK:
        _STREAM_BUFFER = (_STREAM_BUFFER + text)[-_LEADER_STREAM_MAX:]
        _STREAM_UPDATED_AT = time.time()


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
    node   = str(node)
    status = str(status)
    s      = load_session()
    arr    = s.get("workflow_list_nodes_state")
    if not isinstance(arr, list):
        arr = []
    found = False
    for item in arr:
        if isinstance(item, dict) and str(item.get("node")) == node:
            item["status"]     = status
            item["detail"]     = detail[:500]
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
        s["pipeline_active_step"]             = "ambassador"
        s["pipeline_busy_ts"]                 = time.time()
        s["pipeline_active_step_updated_at"]  = time.time()
    save_session(s)


def set_pipeline_after_ambassador(brief) -> None:
    s = load_session()
    s["pipeline_ambassador_status"]      = "done"
    s["pipeline_brief_tier"]             = getattr(brief, "tier", None) or "MEDIUM"
    s["pipeline_brief_selected_leader"]  = getattr(brief, "selected_leader", None) or ""
    s["pipeline_active_step"]            = "idle"
    save_session(s)


def set_pipeline_ambassador_error() -> None:
    s = load_session()
    s["pipeline_ambassador_status"] = "error"
    s["pipeline_active_step"]       = "ambassador"
    save_session(s)


def touch_pipeline_busy() -> None:
    s = load_session()
    s["pipeline_busy_ts"] = time.time()
    save_session(s)


def set_pipeline_active_step(step: str) -> None:
    s   = load_session()
    now = time.time()
    s["pipeline_active_step"]             = step
    s["pipeline_active_step_updated_at"]  = now
    s["pipeline_busy_ts"]                 = now
    if step != "human_context_gate":
        s["pipeline_paused_at_gate"] = False
    save_session(s)


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




# ── Clarification mechanism ───────────────────────────────────────────────────
# When ambassador/leader detect ambiguous input, they pause and ask user.

def set_clarification(question: str, options: list[str]) -> None:
    """Set clarification question + options, signal TUI to show UI."""
    s = load_session()
    s["clarification_pending"]  = True
    s["clarification_question"] = str(question)
    s["clarification_options"]  = list(options)
    s.pop("clarification_answer", None)
    save_session(s)


def is_clarification_pending() -> bool:
    """Return True if waiting for user to answer clarification."""
    return bool(load_session().get("clarification_pending"))


def get_clarification() -> dict | None:
    """Return {question, options} if pending, else None."""
    s = load_session()
    if not s.get("clarification_pending"):
        return None
    return {
        "pending":  True,
        "question": str(s.get("clarification_question") or ""),
        "options":  list(s.get("clarification_options") or []),
    }


def answer_clarification(answer: str) -> None:
    """User answered — store answer and clear pending flag."""
    s = load_session()
    s["clarification_pending"] = False
    s["clarification_answer"]  = str(answer)
    save_session(s)


def get_clarification_answer() -> str:
    """Return the user's clarification answer (empty string if none)."""
    return str(load_session().get("clarification_answer") or "")


def clear_clarification() -> None:
    """Reset all clarification state (call after answer is consumed)."""
    s = load_session()
    s["clarification_pending"] = False
    s.pop("clarification_question", None)
    s.pop("clarification_options",  None)
    s.pop("clarification_answer",   None)
    save_session(s)

def get_pipeline_snapshot() -> dict[str, Any]:
    s = load_session()
    return {
        "active_step":              s.get("pipeline_active_step") or "idle",
        "ambassador_status":        s.get("pipeline_ambassador_status") or "idle",
        "brief_tier":               s.get("pipeline_brief_tier"),
        "brief_selected_leader":    str(s.get("pipeline_brief_selected_leader") or ""),
        "graph_failed":             bool(s.get("pipeline_graph_failed")),
        "paused_at_gate":           bool(s.get("pipeline_paused_at_gate")),
        "run_finished":             _RUN_FINISHED.is_set(),
        "stop_phase":               str(s.get("pipeline_stop_phase") or "idle"),
        "active_step_updated_at":   float(s.get("pipeline_active_step_updated_at") or 0.0),
        "busy_ts":                  float(s.get("pipeline_busy_ts") or 0.0),
        "status_message":           str(s.get("pipeline_status_message") or ""),
        "toast":                    get_pipeline_toast_text(),
        "context_accept_status":    str(s.get("context_accept_status") or "none"),
        "leader_stream_buffer":     _STREAM_BUFFER,
        "leader_stream_updated_at": _STREAM_UPDATED_AT,
        "notifications":            list_active_notifications(),
        "workflow_last_view_mode":  str(s.get("workflow_last_view_mode") or "chain"),
        "workflow_list_nodes_state": list(get_workflow_list_nodes_state()),
        "workflow_list_timeline":   list(get_workflow_list_timeline(120)),
    }
