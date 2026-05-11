"""Text reading helpers for terminal viewers."""

from __future__ import annotations

from pathlib import Path


def safe_read_text(path: str | Path, *, encoding: str = "utf-8") -> str:
    return Path(path).read_text(encoding=encoding, errors="replace")


__all__ = ["safe_read_text"]
