"""Subprocess-based sandbox for project commands."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .policy import is_command_safe

_MAX_OUTPUT = 2 * 1024 * 1024
_SENSITIVE_MARKERS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "OPENROUTER", "OPENAI")


@dataclass(frozen=True, slots=True)
class SandboxResult:
    cmd: str
    returncode: int
    output: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.returncode == 0 and not self.timed_out


def _safe_env(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    keep = {
        "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
        "HOME", "USERPROFILE", "PYTHONPATH", "VIRTUAL_ENV", "APPDATA", "LOCALAPPDATA",
    }
    env = {k: v for k, v in os.environ.items() if k.upper() in keep}
    for key in list(env):
        up = key.upper()
        if any(marker in up for marker in _SENSITIVE_MARKERS):
            env.pop(key, None)
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    env.setdefault("PYTHONIOENCODING", "utf-8")
    return env


def _parse_argv(cmd: str) -> list[str] | None:
    """Parse *cmd* into an argv list. Returns None if parsing fails."""
    try:
        if sys.platform == "win32":
            return shlex.split(cmd, posix=False)
        return shlex.split(cmd)
    except ValueError:
        return None


def run_sandboxed(
    cmd: str,
    cwd: str | Path,
    timeout: int = 120,
    env_overrides: Mapping[str, str] | None = None,
    use_project_venv: bool = False,
) -> SandboxResult:
    safe, reason = is_command_safe(cmd)
    if not safe:
        return SandboxResult(cmd=cmd, returncode=126, output=f"BLOCKED: {reason}")

    argv = _parse_argv(cmd)
    if not argv:
        return SandboxResult(cmd=cmd, returncode=126, output="BLOCKED: command parse failed")

    root = Path(cwd).resolve()
    if not root.exists() or not root.is_dir():
        return SandboxResult(cmd=cmd, returncode=1, output=f"Invalid cwd: {root}")

    flags = 0
    if sys.platform == "win32":
        flags |= getattr(subprocess, "CREATE_NO_WINDOW", 0)

    merged_env = dict(env_overrides or {})
    if use_project_venv:
        try:
            from core.sandbox.venv_manager import venv_env_overrides
            merged_env.update(venv_env_overrides(root))
        except Exception as exc:
            return SandboxResult(cmd=cmd, returncode=1, output=f"Could not prepare project venv: {exc}")

    try:
        proc = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(root),
            timeout=timeout,
            env=_safe_env(merged_env),
            creationflags=flags,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if len(out) > _MAX_OUTPUT:
            out = out[:_MAX_OUTPUT] + "\n...[output truncated]"
        return SandboxResult(cmd=cmd, returncode=proc.returncode, output=out.strip())
    except subprocess.TimeoutExpired as exc:
        out = ((exc.stdout or "") if isinstance(exc.stdout, str) else "") + (
            (exc.stderr or "") if isinstance(exc.stderr, str) else ""
        )
        return SandboxResult(cmd=cmd, returncode=124, output=(out.strip() or f"Timeout after {timeout}s"), timed_out=True)
    except (OSError, FileNotFoundError) as exc:
        return SandboxResult(cmd=cmd, returncode=1, output=str(exc))


__all__ = ["SandboxResult", "run_sandboxed"]
