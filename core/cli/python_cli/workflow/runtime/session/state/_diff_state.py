"""In-memory update diff tracker — collects file changes for TUI display."""
from __future__ import annotations

import threading
import time

_UPDATE_LOCK = threading.Lock()
_UPDATE_DIFFS: list = []


def push_update_diff(
    file_path: str,
    added: int,
    removed: int,
    diff_lines: list,
    status: str = "UPDATE",
    *,
    role_name: str = "",
    full_new_content: str = "",
    old_content: str = "",
) -> None:
    with _UPDATE_LOCK:
        _UPDATE_DIFFS.append({
            "file_path":        file_path,
            "added":            added,
            "removed":          removed,
            "diff_lines":       list(diff_lines),
            "status":           str(status or "UPDATE").upper(),
            "role_name":        role_name,
            "full_new_content": full_new_content,
            "old_content":      old_content,
            "ts":               time.time(),
        })


def get_update_diffs() -> list:
    with _UPDATE_LOCK:
        return list(_UPDATE_DIFFS)


def pop_update_diffs() -> list:
    global _UPDATE_DIFFS
    with _UPDATE_LOCK:
        result = list(_UPDATE_DIFFS)
        _UPDATE_DIFFS = []
        return result


def clear_update_diffs() -> None:
    global _UPDATE_DIFFS
    with _UPDATE_LOCK:
        _UPDATE_DIFFS = []


__all__ = ["push_update_diff", "get_update_diffs", "pop_update_diffs", "clear_update_diffs"]
