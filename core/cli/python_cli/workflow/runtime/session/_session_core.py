"""Session I/O, thread ID management, and constants."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from utils.file_manager import ensure_db_dir, ensure_workflow_dir
from .session_store import load_session_data, save_session_data, session_file

SESSION_FILE = session_file()
WORKFLOW_PHASES = {"idle", "running", "paused_gate"}
CONTEXT_ACCEPT_STATUSES = {"none", "pending", "accepted", "deferred"}


def _ensure_dir() -> None:
    ensure_workflow_dir().mkdir(parents=True, exist_ok=True)


def load_session() -> dict[str, Any]:
    return load_session_data(SESSION_FILE)


def save_session(data: dict[str, Any]) -> None:
    save_session_data(SESSION_FILE, data)


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


def checkpoint_db_path() -> Path:
    return ensure_db_dir() / "langgraph_checkpoints.db"
