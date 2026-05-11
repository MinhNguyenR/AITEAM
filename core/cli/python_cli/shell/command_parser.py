"""Small helpers for slash-command parsing."""

from __future__ import annotations


def normalize_input(raw: str) -> str:
    return (raw or "").strip().lower()


def is_slash_command(raw: str) -> bool:
    return normalize_input(raw).startswith("/")


def slash_head(raw: str) -> str:
    text = normalize_input(raw)
    return text.split(None, 1)[0] if text else ""


def slash_payload(raw: str) -> str:
    text = (raw or "").strip()
    parts = text.split(None, 1)
    return parts[1].strip() if len(parts) > 1 else ""


def slash_required_hint(raw: str) -> str:
    text = normalize_input(raw)
    if not text:
        return ""
    head = text.split(None, 1)[0]
    return f"/{head}" if not head.startswith("/") else head


__all__ = [
    "is_slash_command",
    "normalize_input",
    "slash_head",
    "slash_payload",
    "slash_required_hint",
]
