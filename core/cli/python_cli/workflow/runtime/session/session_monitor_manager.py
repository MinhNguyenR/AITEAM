"""Monitor process PID management for workflow sessions."""

from __future__ import annotations

from ._session_core import load_session, save_session


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
