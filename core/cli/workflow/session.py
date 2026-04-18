"""Shared workflow session (thread_id, pause flags, monitor PID, pipeline UI bridge)."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from utils.file_manager import ensure_db_dir, ensure_workflow_dir

SESSION_FILE = ensure_workflow_dir() / "workflow_session.json"
WORKFLOW_PHASES = {"idle", "running", "paused_gate"}
CONTEXT_ACCEPT_STATUSES = {"none", "pending", "accepted", "deferred"}


def _ensure_dir() -> None:
    ensure_workflow_dir().mkdir(parents=True, exist_ok=True)


def load_session() -> dict[str, Any]:
    if not SESSION_FILE.is_file():
        return {}
    try:
        return json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_session(data: dict[str, Any]) -> None:
    """Write session JSON atomically (temp + replace)."""
    _ensure_dir()
    tmp = SESSION_FILE.with_name(SESSION_FILE.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, SESSION_FILE)


def get_thread_id() -> str | None:
    tid = load_session().get("thread_id")
    return str(tid) if tid else None


def set_thread_id(thread_id: str | None) -> None:
    s = load_session()
    if thread_id:
        s["thread_id"] = thread_id
    else:
        s.pop("thread_id", None)
    save_session(s)


def new_thread_id() -> str:
    tid = str(uuid.uuid4())
    set_thread_id(tid)
    return tid


def set_paused_for_review(paused: bool, context_path: str | None = None) -> None:
    s = load_session()
    s["paused_for_review"] = paused
    if context_path is not None:
        s["context_path"] = context_path
    elif not paused:
        s.pop("context_path", None)
    save_session(s)


def is_paused_for_review() -> bool:
    return bool(load_session().get("paused_for_review"))


def set_last_node(node: str | None) -> None:
    s = load_session()
    if node:
        s["last_node"] = node
    else:
        s.pop("last_node", None)
    save_session(s)


def get_context_path() -> str | None:
    p = load_session().get("context_path")
    return str(p) if p else None


def signal_check_done() -> None:
    s = load_session()
    s["check_done"] = True
    save_session(s)


def consume_check_done() -> bool:
    s = load_session()
    if s.pop("check_done", False):
        save_session(s)
        return True
    return False


def set_should_finalize(flag: bool) -> None:
    s = load_session()
    if flag:
        s["should_finalize"] = True
    else:
        s.pop("should_finalize", None)
    save_session(s)


def peek_should_finalize() -> bool:
    return bool(load_session().get("should_finalize"))


def consume_should_finalize() -> bool:
    s = load_session()
    if s.pop("should_finalize", False):
        save_session(s)
        return True
    return False


def set_interrupt_before(nodes: list[str]) -> None:
    s = load_session()
    s["interrupt_before"] = nodes
    save_session(s)


def get_interrupt_before() -> tuple[str, ...]:
    s = load_session()
    raw = s.get("interrupt_before") or []
    return tuple(str(x) for x in raw)


def checkpoint_db_path() -> Path:
    return ensure_db_dir() / "langgraph_checkpoints.db"


def clear_session_flags() -> None:
    s = load_session()
    for k in ("paused_for_review", "check_done", "last_node"):
        s.pop(k, None)
    save_session(s)


# --- Monitor process ---


def get_monitor_pid() -> int | None:
    p = load_session().get("monitor_pid")
    if p is None:
        return None
    try:
        return int(p)
    except (TypeError, ValueError):
        return None


def set_monitor_pid(pid: int | None) -> None:
    s = load_session()
    if pid is not None and pid > 0:
        s["monitor_pid"] = pid
    else:
        s.pop("monitor_pid", None)
    save_session(s)


def clear_monitor_pid() -> None:
    s = load_session()
    s.pop("monitor_pid", None)
    save_session(s)


# --- Pipeline visual (Textual monitor) ---


def get_workflow_activity_min_ts() -> float:
    try:
        return float(load_session().get("workflow_activity_min_ts") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def reset_pipeline_visual() -> None:
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
    s["context_accept_status"] = "none"
    s["pipeline_notifications"] = []
    s["dismissed_notification_ids"] = []
    s["leader_stream_buffer"] = ""
    s["leader_stream_updated_at"] = 0.0
    s["workflow_list_nodes_state"] = []
    s["workflow_list_timeline"] = []
    save_session(s)


def apply_stale_workflow_ui_if_needed(project_root: str) -> None:
    from core.cli.context_flow import find_context_md, is_no_context

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
    s["leader_stream_buffer"] = ""
    s["leader_stream_updated_at"] = 0.0
    s["workflow_list_nodes_state"] = []
    s["pipeline_status_message"] = ""
    s["context_accept_status"] = "none"
    save_session(s)


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


def get_pipeline_status_message() -> str:
    return str(load_session().get("pipeline_status_message") or "")


def push_pipeline_notification(
    title: str,
    body: str,
    kind: str,
    extra: dict[str, Any] | None = None,
) -> str:
    nid = str(uuid.uuid4())
    s = load_session()
    items = s.get("pipeline_notifications")
    if not isinstance(items, list):
        items = []
    items.append(
        {
            "id": nid,
            "title": str(title)[:200],
            "body": str(body)[:2000],
            "kind": kind,
            "extra": dict(extra or {}),
            "ts": time.time(),
        }
    )
    s["pipeline_notifications"] = items[-25:]
    save_session(s)
    return nid


def list_active_notifications() -> list[dict[str, Any]]:
    s = load_session()
    items = s.get("pipeline_notifications")
    dismissed = s.get("dismissed_notification_ids")
    if not isinstance(items, list):
        return []
    if not isinstance(dismissed, list):
        dismissed = []
    dis = {str(x) for x in dismissed}
    return [x for x in items if isinstance(x, dict) and str(x.get("id")) not in dis]


def dismiss_pipeline_notification(nid: str) -> None:
    s = load_session()
    d = s.get("dismissed_notification_ids")
    if not isinstance(d, list):
        d = []
    if nid not in d:
        d.append(nid)
    s["dismissed_notification_ids"] = d[-200:]
    save_session(s)


def prune_stale_pipeline_notifications() -> None:
    s = load_session()
    items = s.get("pipeline_notifications")
    if not isinstance(items, list):
        return
    d = s.get("dismissed_notification_ids")
    if not isinstance(d, list):
        d = []
    dis = {str(x) for x in d}
    changed = False
    for n in items:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id", ""))
        if not nid or nid in dis:
            continue
        extra = n.get("extra") if isinstance(n.get("extra"), dict) else {}
        kind = str(n.get("kind", ""))
        path = None
        if kind == "context_ready":
            path = extra.get("context_path")
        elif kind == "state_json_ready":
            path = extra.get("state_path")
        if not path:
            continue
        try:
            missing = not Path(path).is_file()
        except OSError:
            missing = True
        if missing:
            d.append(nid)
            changed = True
    if changed:
        s["dismissed_notification_ids"] = d[-200:]
        save_session(s)


def clear_leader_stream_buffer() -> None:
    s = load_session()
    s["leader_stream_buffer"] = ""
    s["leader_stream_updated_at"] = 0.0
    save_session(s)


_LEADER_STREAM_MAX = 48000


def append_leader_stream_chunk(text: str) -> None:
    if not text:
        return
    s = load_session()
    cur = str(s.get("leader_stream_buffer") or "")
    cur = cur + text
    if len(cur) > _LEADER_STREAM_MAX:
        cur = cur[-_LEADER_STREAM_MAX:]
    s["leader_stream_buffer"] = cur
    s["leader_stream_updated_at"] = time.time()
    save_session(s)


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
        arr.append(
            {
                "node": node,
                "status": status,
                "detail": detail[:500],
                "updated_at": time.time(),
            }
        )
    s["workflow_list_nodes_state"] = arr[-30:]
    tl = s.get("workflow_list_timeline")
    if not isinstance(tl, list):
        tl = []
    tl.append(
        {
            "ts": time.time(),
            "node": node,
            "status": status,
            "detail": detail[:500],
        }
    )
    s["workflow_list_timeline"] = tl[-300:]
    save_session(s)


def set_pipeline_ambassador_status(status: str) -> None:
    """idle | running | done | error"""
    s = load_session()
    s["pipeline_ambassador_status"] = status
    if status == "running":
        s["pipeline_active_step"] = "ambassador"
        s["pipeline_busy_ts"] = time.time()
        s["pipeline_active_step_updated_at"] = time.time()
    save_session(s)


def set_pipeline_after_ambassador(brief) -> None:
    """Call after successful parse; brief has tier, selected_leader."""
    s = load_session()
    s["pipeline_ambassador_status"] = "done"
    s["pipeline_brief_tier"] = getattr(brief, "tier", None) or "MEDIUM"
    s["pipeline_brief_selected_leader"] = getattr(brief, "selected_leader", None) or ""
    s["pipeline_active_step"] = "idle"
    save_session(s)


def set_pipeline_ambassador_error() -> None:
    s = load_session()
    s["pipeline_ambassador_status"] = "error"
    s["pipeline_active_step"] = "ambassador"
    save_session(s)


def touch_pipeline_busy() -> None:
    """Heartbeat while a graph node runs (LLM); monitor uses for blink."""
    s = load_session()
    s["pipeline_busy_ts"] = time.time()
    save_session(s)


def set_pipeline_active_step(step: str) -> None:
    s = load_session()
    now = time.time()
    s["pipeline_active_step"] = step
    s["pipeline_active_step_updated_at"] = now
    s["pipeline_busy_ts"] = now
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


def get_pipeline_snapshot() -> dict[str, Any]:
    s = load_session()
    return {
        "active_step": s.get("pipeline_active_step") or "idle",
        "ambassador_status": s.get("pipeline_ambassador_status") or "idle",
        "brief_tier": s.get("pipeline_brief_tier"),
        "brief_selected_leader": str(s.get("pipeline_brief_selected_leader") or ""),
        "graph_failed": bool(s.get("pipeline_graph_failed")),
        "paused_at_gate": bool(s.get("pipeline_paused_at_gate")),
        "run_finished": bool(s.get("pipeline_run_finished")),
        "stop_phase": str(s.get("pipeline_stop_phase") or "idle"),
        "active_step_updated_at": float(s.get("pipeline_active_step_updated_at") or 0.0),
        "busy_ts": float(s.get("pipeline_busy_ts") or 0.0),
        "status_message": str(s.get("pipeline_status_message") or ""),
        "context_accept_status": str(s.get("context_accept_status") or "none"),
        "leader_stream_buffer": str(s.get("leader_stream_buffer") or ""),
        "leader_stream_updated_at": float(s.get("leader_stream_updated_at") or 0.0),
        "notifications": list_active_notifications(),
        "workflow_last_view_mode": str(s.get("workflow_last_view_mode") or "chain"),
        "workflow_list_nodes_state": list(get_workflow_list_nodes_state()),
        "workflow_list_timeline": list(get_workflow_list_timeline(120)),
    }
