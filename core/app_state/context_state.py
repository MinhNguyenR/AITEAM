from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.storage import ask_history

from ._io import write_secure
from .actions import log_system_action


def _context_state_path() -> Path:
    path = ask_history.ask_data_dir() / "context_state.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def load_context_state() -> dict:
    path = _context_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def save_context_state(state: dict) -> None:
    write_secure(_context_state_path(), json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def update_context_state(
    status: str,
    context_path: Optional[Path] = None,
    reason: str = "",
    task_uuid: str = "",
) -> None:
    state = load_context_state()
    now = datetime.now().isoformat()
    state.update(
        {
            "context_path": str(context_path) if context_path else state.get("context_path", ""),
            "status": status,
            "reason": reason,
            "task_uuid": task_uuid or state.get("task_uuid", ""),
            "updated_at": now,
            "created_at": state.get("created_at", now),
        }
    )
    save_context_state(state)
    log_system_action(
        "context.state.change",
        f"status={status} reason={reason} path={state.get('context_path', '')}",
    )


def is_context_active() -> bool:
    return load_context_state().get("status") == "active"


__all__ = [
    "is_context_active",
    "load_context_state",
    "save_context_state",
    "update_context_state",
]
