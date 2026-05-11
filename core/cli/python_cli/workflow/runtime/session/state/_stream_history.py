"""TUI stream history persistence — in-memory list backed by a separate JSON file."""
from __future__ import annotations

import json
import os
import threading

_STREAM_HISTORY_MAX = 1000
_STREAM_HISTORY_LOCK = threading.Lock()
_STREAM_HISTORY: list[str] = []
_STREAM_HISTORY_LOADED = False


def _stream_history_file() -> str:
    from .._session_core import SESSION_FILE
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
    try:
        from .._session_core import load_session
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
    with _STREAM_HISTORY_LOCK:
        _load_history_once()
        _STREAM_HISTORY.append(str(line))
        if len(_STREAM_HISTORY) > _STREAM_HISTORY_MAX:
            del _STREAM_HISTORY[:-_STREAM_HISTORY_MAX]
    _save_history_bg()


def get_stream_history() -> list[str]:
    with _STREAM_HISTORY_LOCK:
        _load_history_once()
        return list(_STREAM_HISTORY)


def clear_stream_history() -> None:
    global _STREAM_HISTORY_LOADED
    with _STREAM_HISTORY_LOCK:
        _STREAM_HISTORY.clear()
        _STREAM_HISTORY_LOADED = True
    _save_history_bg()


__all__ = ["append_stream_line", "get_stream_history", "clear_stream_history"]
