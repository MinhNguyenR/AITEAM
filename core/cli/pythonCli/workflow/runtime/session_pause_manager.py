"""Pause/finalize/interrupt signal management for workflow sessions."""

from __future__ import annotations

from typing import Any

from ._session_core import load_session, save_session


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


def clear_session_flags() -> None:
    s = load_session()
    for k in ("paused_for_review", "check_done", "last_node"):
        s.pop(k, None)
    save_session(s)
