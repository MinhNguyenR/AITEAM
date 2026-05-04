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

# ── In-memory reasoning/thinking stream buffer ───────────────────────────────
_REASONING_LOCK    = threading.Lock()
_REASONING_BUFFER: str  = ""
_REASONING_ACTIVE: bool = False  # True while model is in reasoning/thinking phase
_REASONING_DONE:   bool = False  # Flipped True once when reasoning ends (TUI reads+clears)
_REASONING_MAX = 48_000

# ── Real-time token tracking (not capped by 12k display buffer) ───────────────
_TOKEN_LOCK             = threading.Lock()
_STREAM_CHAR_COUNT:   int = 0   # total output chars streamed (accurate token estimate)
_STREAM_PROMPT_TOKENS: int = 0   # prompt tokens from streaming usage chunk
_STREAM_COMPLETION_TOKENS: int = 0

# ── Leader action tracker (shown in TUI live view before stream arrives) ──────
_LEADER_ACTION_LOCK  = threading.Lock()
_LEADER_ACTION:       str = ""  # e.g. "reading state.json", "preparing context"

# ── Tool Curator substate tracker (reading → thinking → looking_for → writing) ─
_CURATOR_LOCK     = threading.Lock()
_CURATOR_SUBSTATE: str = ""  # one of: "reading","thinking","looking_for","writing"
_CURATOR_DETAIL:   str = ""  # free-form one-line detail (e.g. file glob, pkg list)
_CURATOR_STARTED_AT: float = 0.0
_CURATOR_SUBSTATE_AT: float = 0.0

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
# In-memory store + separate file (NOT session.json) to avoid race conditions.
# Multiple threads write session.json concurrently; using a dedicated file and
# an in-memory list eliminates TOCTOU overwrites that were losing history.

import json
import os

_STREAM_HISTORY_MAX  = 1000
_STREAM_HISTORY_LOCK = threading.Lock()
_STREAM_HISTORY: list[str] = []
_STREAM_HISTORY_LOADED = False


def _stream_history_file() -> str:
    from ._session_core import SESSION_FILE
    return os.path.join(os.path.dirname(SESSION_FILE), "tui_stream_history.json")


def _load_history_once() -> None:
    global _STREAM_HISTORY_LOADED
    if _STREAM_HISTORY_LOADED:
        return
    _STREAM_HISTORY_LOADED = True
    try:
        path = _stream_history_file()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                _STREAM_HISTORY.extend([str(x) for x in data[-_STREAM_HISTORY_MAX:]])
            return
    except Exception:
        pass
    # Fallback: migrate from old session.json location
    try:
        hist = load_session().get("tui_stream_history")
        if isinstance(hist, list):
            _STREAM_HISTORY.extend([str(x) for x in hist[-_STREAM_HISTORY_MAX:]])
    except Exception:
        pass


def _save_history_bg() -> None:
    with _STREAM_HISTORY_LOCK:
        data = list(_STREAM_HISTORY)
    def _write():
        try:
            path = _stream_history_file()
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass
    threading.Thread(target=_write, daemon=True).start()


def append_stream_line(line: str) -> None:
    """Append a Rich-markup line to the persistent TUI stream history."""
    with _STREAM_HISTORY_LOCK:
        _load_history_once()
        _STREAM_HISTORY.append(str(line))
        if len(_STREAM_HISTORY) > _STREAM_HISTORY_MAX:
            del _STREAM_HISTORY[:-_STREAM_HISTORY_MAX]
    _save_history_bg()


def get_stream_history() -> list[str]:
    """Return all persisted TUI stream lines (for replaying on TUI mount)."""
    with _STREAM_HISTORY_LOCK:
        _load_history_once()
        return list(_STREAM_HISTORY)


def clear_stream_history() -> None:
    """Clear stream history. Only called when user declines and regenerates."""
    global _STREAM_HISTORY_LOADED
    with _STREAM_HISTORY_LOCK:
        _STREAM_HISTORY.clear()
        _STREAM_HISTORY_LOADED = True
    _save_history_bg()


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
    # tui_stream_history intentionally preserved
    save_session(s)
    clear_leader_stream_buffer()
    clear_reasoning_buffer()
    reset_stream_token_counters()
    clear_leader_action()


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


def set_reasoning_active(active: bool) -> None:
    global _REASONING_ACTIVE, _REASONING_DONE
    with _REASONING_LOCK:
        if _REASONING_ACTIVE and not active:
            _REASONING_DONE = True
        _REASONING_ACTIVE = active


def is_reasoning_active() -> bool:
    with _REASONING_LOCK:
        return _REASONING_ACTIVE


def append_reasoning_chunk(text: str) -> None:
    global _REASONING_BUFFER
    if not text:
        return
    with _REASONING_LOCK:
        _REASONING_BUFFER = (_REASONING_BUFFER + text)[-_REASONING_MAX:]


def drain_reasoning_buffer() -> tuple[str, bool, bool]:
    """Return (new_chunks, is_active, just_ended).
    just_ended is True for exactly ONE drain call when reasoning transitions active→done.
    """
    global _REASONING_BUFFER, _REASONING_DONE
    with _REASONING_LOCK:
        chunk = _REASONING_BUFFER
        _REASONING_BUFFER = ""
        active = _REASONING_ACTIVE
        ended = _REASONING_DONE
        _REASONING_DONE = False
        return chunk, active, ended


def clear_reasoning_buffer() -> None:
    global _REASONING_BUFFER, _REASONING_ACTIVE, _REASONING_DONE
    with _REASONING_LOCK:
        _REASONING_BUFFER = ""
        _REASONING_ACTIVE = False
        _REASONING_DONE = False


# ── Real-time token tracking ──────────────────────────────────────────────────

def increment_stream_char_count(n: int) -> None:
    global _STREAM_CHAR_COUNT
    with _TOKEN_LOCK:
        _STREAM_CHAR_COUNT += n


def get_stream_char_count() -> int:
    with _TOKEN_LOCK:
        return _STREAM_CHAR_COUNT


def set_stream_prompt_tokens(n: int) -> None:
    global _STREAM_PROMPT_TOKENS
    with _TOKEN_LOCK:
        if n > _STREAM_PROMPT_TOKENS:
            _STREAM_PROMPT_TOKENS = n


def get_stream_prompt_tokens() -> int:
    with _TOKEN_LOCK:
        return _STREAM_PROMPT_TOKENS


def set_stream_completion_tokens(n: int) -> None:
    global _STREAM_COMPLETION_TOKENS
    with _TOKEN_LOCK:
        if n > _STREAM_COMPLETION_TOKENS:
            _STREAM_COMPLETION_TOKENS = n


def get_stream_completion_tokens() -> int:
    with _TOKEN_LOCK:
        if _STREAM_COMPLETION_TOKENS > 0:
            return _STREAM_COMPLETION_TOKENS
        return _STREAM_CHAR_COUNT // 4


def reset_stream_token_counters() -> None:
    global _STREAM_CHAR_COUNT, _STREAM_PROMPT_TOKENS, _STREAM_COMPLETION_TOKENS
    with _TOKEN_LOCK:
        _STREAM_CHAR_COUNT = 0
        _STREAM_PROMPT_TOKENS = 0
        _STREAM_COMPLETION_TOKENS = 0


# ── Leader action tracker ─────────────────────────────────────────────────────

def set_leader_action(action: str) -> None:
    global _LEADER_ACTION
    with _LEADER_ACTION_LOCK:
        _LEADER_ACTION = str(action or "")


def get_leader_action() -> str:
    with _LEADER_ACTION_LOCK:
        return _LEADER_ACTION


def clear_leader_action() -> None:
    global _LEADER_ACTION
    with _LEADER_ACTION_LOCK:
        _LEADER_ACTION = ""


# ── Tool Curator substate ─────────────────────────────────────────────────────

_CURATOR_VALID_SUBSTATES = frozenset({"reading", "thinking", "looking_for", "writing"})


def set_curator_substate(substate: str, detail: str = "") -> None:
    global _CURATOR_SUBSTATE, _CURATOR_DETAIL, _CURATOR_SUBSTATE_AT, _CURATOR_STARTED_AT
    sub = str(substate or "").strip().lower()
    if sub and sub not in _CURATOR_VALID_SUBSTATES:
        sub = ""
    with _CURATOR_LOCK:
        if sub and not _CURATOR_STARTED_AT:
            _CURATOR_STARTED_AT = time.time()
        _CURATOR_SUBSTATE    = sub
        _CURATOR_DETAIL      = str(detail or "")[:200]
        _CURATOR_SUBSTATE_AT = time.time() if sub else 0.0


def get_curator_substate() -> dict[str, Any]:
    with _CURATOR_LOCK:
        return {
            "substate":     _CURATOR_SUBSTATE,
            "detail":       _CURATOR_DETAIL,
            "started_at":   _CURATOR_STARTED_AT,
            "substate_at":  _CURATOR_SUBSTATE_AT,
        }


def clear_curator_substate() -> None:
    global _CURATOR_SUBSTATE, _CURATOR_DETAIL, _CURATOR_STARTED_AT, _CURATOR_SUBSTATE_AT
    with _CURATOR_LOCK:
        _CURATOR_SUBSTATE    = ""
        _CURATOR_DETAIL      = ""
        _CURATOR_STARTED_AT  = 0.0
        _CURATOR_SUBSTATE_AT = 0.0


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


def clear_leader_stream_buffer() -> None:
    global _STREAM_BUFFER, _STREAM_UPDATED_AT
    with _STREAM_LOCK:
        _STREAM_BUFFER = ""
        _STREAM_UPDATED_AT = 0.0
    reset_stream_token_counters()
    clear_leader_action()


def append_leader_stream_chunk(text: str) -> None:
    global _STREAM_BUFFER, _STREAM_UPDATED_AT
    if not text:
        return
    with _STREAM_LOCK:
        _STREAM_BUFFER = (_STREAM_BUFFER + text)[-_LEADER_STREAM_MAX:]
        _STREAM_UPDATED_AT = time.time()


def drain_leader_stream_buffer() -> str:
    """Read all buffered stream content and atomically clear the buffer."""
    global _STREAM_BUFFER
    with _STREAM_LOCK:
        result = _STREAM_BUFFER
        _STREAM_BUFFER = ""
        return result


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
    s["pipeline_busy_ts"]                = time.time()  # reset so chain spin window starts from completion
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


def transition_pipeline_begin_run() -> None:
    """Atomic: begin a new run, reset run_finished/paused/failed flags in one save."""
    _RUN_FINISHED.clear()
    s = load_session()
    s["pipeline_run_finished"]   = False
    s["pipeline_paused_at_gate"] = False
    s["pipeline_graph_failed"]   = False
    s["pipeline_busy_ts"]        = time.time()
    save_session(s)


def transition_pipeline_active(step: str) -> None:
    """Atomic equivalent of set_pipeline_active_step but with single save (alias kept for clarity)."""
    set_pipeline_active_step(step)


def transition_pipeline_finish(*, failed: bool = False) -> None:
    """Atomic: finish run (success or fail) clearing active_step and toggling flags in one save."""
    if failed:
        _RUN_FINISHED.set()
    else:
        _RUN_FINISHED.set()
    s = load_session()
    s["pipeline_run_finished"] = True
    s["pipeline_graph_failed"] = bool(failed)
    s["pipeline_active_step"]  = "idle"
    save_session(s)


def transition_pipeline_pause_at_gate() -> None:
    """Atomic: paused for review at human gate."""
    s = load_session()
    s["pipeline_paused_at_gate"] = True
    s["pipeline_active_step"]   = "human_context_gate"
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




# ── Clarification mechanism ───────────────────────────────────────────────────
# When ambassador/leader detect ambiguous input, they pause and ask user.

def set_clarification(q_list: list[dict]) -> None:
    """Set clarification questions list, signal TUI to show UI."""
    s = load_session()
    s["clarification_pending"]  = True
    s["clarification_q_list"]   = list(q_list)
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
        "q_list":   list(s.get("clarification_q_list") or []),
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
