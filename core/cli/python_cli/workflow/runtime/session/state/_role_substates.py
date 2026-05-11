"""In-memory role substate trackers: curator, ambassador, leader, worker, secretary, explainer."""
from __future__ import annotations

import threading
import time
from typing import Any

# -- Tool Curator --------------------------------------------------------------
_CURATOR_LOCK = threading.Lock()
_CURATOR_SUBSTATE: str = ""
_CURATOR_DETAIL: str = ""
_CURATOR_STARTED_AT: float = 0.0
_CURATOR_SUBSTATE_AT: float = 0.0
_CURATOR_VALID_SUBSTATES = frozenset({"reading", "thinking", "looking_for", "writing"})

# -- Ambassador ----------------------------------------------------------------
_AMBASSADOR_LOCK = threading.Lock()
_AMBASSADOR_SUBSTATE: str = ""
_AMBASSADOR_DETAIL: str = ""
_AMBASSADOR_STARTED_AT: float = 0.0
_AMBASSADOR_SUBSTATE_AT: float = 0.0
_AMBASSADOR_VALID_SUBSTATES = frozenset({"reading", "thinking", "writing"})

# -- Leader substate -----------------------------------------------------------
_LEADER_SUB_LOCK = threading.Lock()
_LEADER_SUBSTATE: str = ""
_LEADER_DETAIL: str = ""
_LEADER_SUBSTATE_AT: float = 0.0
_LEADER_VALID_SUBSTATES = frozenset({"reading", "thinking", "writing"})

# -- Worker (per-worker-key) ---------------------------------------------------
_WORKER_LOCK = threading.Lock()
_WORKER_SUBSTATES: dict = {}
_WORKER_DETAILS: dict = {}
_WORKER_READING: dict = {}
_WORKER_COMMANDS: dict = {}
_WORKER_USING_CMD: dict = {}

# -- Secretary -----------------------------------------------------------------
_SECRETARY_LOCK = threading.Lock()
_SECRETARY_SUBSTATE: str = ""
_SECRETARY_DETAIL: str = ""
_SECRETARY_COMMANDS: list = []
_SECRETARY_VALID_SUBSTATES = frozenset({"asking", "using", "fallback"})

# -- Explainer -----------------------------------------------------------------
_EXPLAINER_LOCK = threading.Lock()
_EXPLAINER_SUBSTATE: str = ""
_EXPLAINER_DETAIL: str = ""


# Curator ----------------------------------------------------------------------

def set_curator_substate(substate: str, detail: str = "") -> None:
    global _CURATOR_SUBSTATE, _CURATOR_DETAIL, _CURATOR_SUBSTATE_AT, _CURATOR_STARTED_AT
    sub = str(substate or "").strip().lower()
    if sub and sub not in _CURATOR_VALID_SUBSTATES:
        sub = ""
    with _CURATOR_LOCK:
        if sub and not _CURATOR_STARTED_AT:
            _CURATOR_STARTED_AT = time.time()
        _CURATOR_SUBSTATE = sub
        _CURATOR_DETAIL = str(detail or "")[:200]
        _CURATOR_SUBSTATE_AT = time.time() if sub else 0.0


def get_curator_substate() -> dict[str, Any]:
    with _CURATOR_LOCK:
        return {
            "substate":    _CURATOR_SUBSTATE,
            "detail":      _CURATOR_DETAIL,
            "started_at":  _CURATOR_STARTED_AT,
            "substate_at": _CURATOR_SUBSTATE_AT,
        }


def clear_curator_substate() -> None:
    global _CURATOR_SUBSTATE, _CURATOR_DETAIL, _CURATOR_STARTED_AT, _CURATOR_SUBSTATE_AT
    with _CURATOR_LOCK:
        _CURATOR_SUBSTATE = ""
        _CURATOR_DETAIL = ""
        _CURATOR_STARTED_AT = 0.0
        _CURATOR_SUBSTATE_AT = 0.0


# Ambassador -------------------------------------------------------------------

def set_ambassador_substate(substate: str, detail: str = "") -> None:
    global _AMBASSADOR_SUBSTATE, _AMBASSADOR_DETAIL, _AMBASSADOR_SUBSTATE_AT, _AMBASSADOR_STARTED_AT
    sub = str(substate or "").strip().lower()
    if sub and sub not in _AMBASSADOR_VALID_SUBSTATES:
        sub = ""
    with _AMBASSADOR_LOCK:
        if sub and not _AMBASSADOR_STARTED_AT:
            _AMBASSADOR_STARTED_AT = time.time()
        _AMBASSADOR_SUBSTATE = sub
        _AMBASSADOR_DETAIL = str(detail or "")[:200]
        _AMBASSADOR_SUBSTATE_AT = time.time() if sub else 0.0


def get_ambassador_substate() -> dict[str, Any]:
    with _AMBASSADOR_LOCK:
        return {
            "substate":    _AMBASSADOR_SUBSTATE,
            "detail":      _AMBASSADOR_DETAIL,
            "started_at":  _AMBASSADOR_STARTED_AT,
            "substate_at": _AMBASSADOR_SUBSTATE_AT,
        }


def clear_ambassador_substate() -> None:
    global _AMBASSADOR_SUBSTATE, _AMBASSADOR_DETAIL, _AMBASSADOR_STARTED_AT, _AMBASSADOR_SUBSTATE_AT
    with _AMBASSADOR_LOCK:
        _AMBASSADOR_SUBSTATE = ""
        _AMBASSADOR_DETAIL = ""
        _AMBASSADOR_STARTED_AT = 0.0
        _AMBASSADOR_SUBSTATE_AT = 0.0


# Leader substate --------------------------------------------------------------

def set_leader_substate(substate: str, detail: str = "") -> None:
    global _LEADER_SUBSTATE, _LEADER_DETAIL, _LEADER_SUBSTATE_AT
    sub = str(substate or "").strip().lower()
    if sub and sub not in _LEADER_VALID_SUBSTATES:
        sub = ""
    with _LEADER_SUB_LOCK:
        _LEADER_SUBSTATE = sub
        _LEADER_DETAIL = str(detail or "")[:200]
        _LEADER_SUBSTATE_AT = time.time() if sub else 0.0


def get_leader_substate() -> dict[str, Any]:
    with _LEADER_SUB_LOCK:
        return {
            "substate":    _LEADER_SUBSTATE,
            "detail":      _LEADER_DETAIL,
            "substate_at": _LEADER_SUBSTATE_AT,
        }


def clear_leader_substate() -> None:
    global _LEADER_SUBSTATE, _LEADER_DETAIL, _LEADER_SUBSTATE_AT
    with _LEADER_SUB_LOCK:
        _LEADER_SUBSTATE = ""
        _LEADER_DETAIL = ""
        _LEADER_SUBSTATE_AT = 0.0


# Worker -----------------------------------------------------------------------

def set_worker_substate(worker_key: str, substate: str, detail: str = "") -> None:
    with _WORKER_LOCK:
        _WORKER_SUBSTATES[worker_key] = substate
        _WORKER_DETAILS[worker_key] = detail


def get_worker_substate(worker_key: str) -> dict:
    with _WORKER_LOCK:
        return {
            "substate": _WORKER_SUBSTATES.get(worker_key, ""),
            "detail":   _WORKER_DETAILS.get(worker_key, ""),
        }


def clear_worker_substate(worker_key: str) -> None:
    with _WORKER_LOCK:
        _WORKER_SUBSTATES.pop(worker_key, None)
        _WORKER_DETAILS.pop(worker_key, None)
        _WORKER_USING_CMD.pop(worker_key, None)


def push_worker_reading_file(worker_key: str, file_path: str) -> None:
    with _WORKER_LOCK:
        lst = _WORKER_READING.setdefault(worker_key, [])
        if file_path not in lst:
            lst.append(file_path)


def get_worker_reading_files(worker_key: str) -> list:
    with _WORKER_LOCK:
        return list(_WORKER_READING.get(worker_key, []))


def clear_worker_reading_files(worker_key: str) -> None:
    with _WORKER_LOCK:
        _WORKER_READING.pop(worker_key, None)


def set_worker_using_command(worker_key: str, cmd: str) -> None:
    with _WORKER_LOCK:
        _WORKER_USING_CMD[worker_key] = cmd


def get_worker_using_command(worker_key: str) -> str:
    with _WORKER_LOCK:
        return _WORKER_USING_CMD.get(worker_key, "")


def push_worker_command_result(worker_key: str, cmd: str, success: bool, output: str) -> None:
    with _WORKER_LOCK:
        lst = _WORKER_COMMANDS.setdefault(worker_key, [])
        lst.append({"cmd": cmd, "success": success, "output": output})


def get_worker_command_results(worker_key: str) -> list:
    with _WORKER_LOCK:
        return list(_WORKER_COMMANDS.get(worker_key, []))


def clear_worker_state(worker_key: str) -> None:
    with _WORKER_LOCK:
        for d in (_WORKER_SUBSTATES, _WORKER_DETAILS, _WORKER_READING,
                  _WORKER_COMMANDS, _WORKER_USING_CMD):
            d.pop(worker_key, None)


# Secretary --------------------------------------------------------------------

def set_secretary_substate(substate: str, detail: str = "") -> None:
    global _SECRETARY_SUBSTATE, _SECRETARY_DETAIL
    sub = str(substate or "").strip().lower()
    if sub and sub not in _SECRETARY_VALID_SUBSTATES:
        sub = ""
    with _SECRETARY_LOCK:
        _SECRETARY_SUBSTATE = sub
        _SECRETARY_DETAIL = str(detail or "")[:240]


def get_secretary_substate() -> dict:
    with _SECRETARY_LOCK:
        return {"substate": _SECRETARY_SUBSTATE, "detail": _SECRETARY_DETAIL}


def clear_secretary_substate() -> None:
    global _SECRETARY_SUBSTATE, _SECRETARY_DETAIL
    with _SECRETARY_LOCK:
        _SECRETARY_SUBSTATE = ""
        _SECRETARY_DETAIL = ""


def push_secretary_command_result(cmd: str, success: bool, output: str) -> None:
    with _SECRETARY_LOCK:
        _SECRETARY_COMMANDS.append({"cmd": cmd, "success": success, "output": output})


def get_secretary_command_results() -> list:
    with _SECRETARY_LOCK:
        return list(_SECRETARY_COMMANDS)


def clear_secretary_commands() -> None:
    with _SECRETARY_LOCK:
        _SECRETARY_COMMANDS.clear()


# Explainer --------------------------------------------------------------------

def set_explainer_substate(substate: str, detail: str = "") -> None:
    global _EXPLAINER_SUBSTATE, _EXPLAINER_DETAIL
    with _EXPLAINER_LOCK:
        _EXPLAINER_SUBSTATE = substate
        _EXPLAINER_DETAIL = detail


def get_explainer_substate() -> dict:
    with _EXPLAINER_LOCK:
        return {"substate": _EXPLAINER_SUBSTATE, "detail": _EXPLAINER_DETAIL}


def clear_explainer_substate() -> None:
    global _EXPLAINER_SUBSTATE, _EXPLAINER_DETAIL
    with _EXPLAINER_LOCK:
        _EXPLAINER_SUBSTATE = ""
        _EXPLAINER_DETAIL = ""


__all__ = [
    "set_curator_substate", "get_curator_substate", "clear_curator_substate",
    "set_ambassador_substate", "get_ambassador_substate", "clear_ambassador_substate",
    "set_leader_substate", "get_leader_substate", "clear_leader_substate",
    "set_worker_substate", "get_worker_substate", "clear_worker_substate",
    "push_worker_reading_file", "get_worker_reading_files", "clear_worker_reading_files",
    "set_worker_using_command", "get_worker_using_command",
    "push_worker_command_result", "get_worker_command_results", "clear_worker_state",
    "set_secretary_substate", "get_secretary_substate", "clear_secretary_substate",
    "push_secretary_command_result", "get_secretary_command_results", "clear_secretary_commands",
    "set_explainer_substate", "get_explainer_substate", "clear_explainer_substate",
]
