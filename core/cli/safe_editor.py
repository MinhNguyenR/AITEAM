"""Launch $EDITOR (or default) with a file path; reject obviously unsafe EDITOR values."""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

_MAX_EDITOR_LEN = 512
_FORBIDDEN_SUBSTR = ("&", "|", ";", "<", ">", "$", "`", "\n", "\r")


def _default_editor() -> str:
    return "notepad" if os.name == "nt" else "nano"


def build_editor_argv(target: Path) -> list[str]:
    raw = (os.environ.get("EDITOR") or "").strip()
    if not raw:
        return [_default_editor(), str(target)]
    if len(raw) > _MAX_EDITOR_LEN:
        return [_default_editor(), str(target)]
    if any(s in raw for s in _FORBIDDEN_SUBSTR):
        return [_default_editor(), str(target)]
    try:
        parts = shlex.split(raw, posix=os.name != "nt")
    except ValueError:
        return [_default_editor(), str(target)]
    if not parts:
        return [_default_editor(), str(target)]
    return [*parts, str(target)]


def run_editor_on_file(target: Path) -> None:
    argv = build_editor_argv(target)
    subprocess.run(argv, check=False, shell=False)


__all__ = ["build_editor_argv", "run_editor_on_file"]
