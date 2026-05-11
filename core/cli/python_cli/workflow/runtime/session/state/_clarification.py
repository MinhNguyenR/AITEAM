"""Clarification mechanism — pause pipeline to ask user for more info."""
from __future__ import annotations

from .._session_core import load_session, save_session


def set_clarification(q_list: list[dict]) -> None:
    s = load_session()
    s["clarification_pending"] = True
    s["clarification_q_list"] = list(q_list)
    s.pop("clarification_answer", None)
    save_session(s)


def is_clarification_pending() -> bool:
    return bool(load_session().get("clarification_pending"))


def get_clarification() -> dict | None:
    s = load_session()
    if not s.get("clarification_pending"):
        return None
    return {
        "pending": True,
        "q_list":  list(s.get("clarification_q_list") or []),
    }


def answer_clarification(answer: str) -> None:
    s = load_session()
    s["clarification_pending"] = False
    s["clarification_answer"] = str(answer)
    save_session(s)


def get_clarification_answer() -> str:
    return str(load_session().get("clarification_answer") or "")


def clear_clarification() -> None:
    s = load_session()
    s["clarification_pending"] = False
    s.pop("clarification_question", None)
    s.pop("clarification_options", None)
    s.pop("clarification_answer", None)
    save_session(s)


__all__ = [
    "set_clarification", "is_clarification_pending", "get_clarification",
    "answer_clarification", "get_clarification_answer", "clear_clarification",
]
