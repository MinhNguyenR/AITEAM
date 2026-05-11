"""Terminal skill backed by the sandbox executor."""

from __future__ import annotations

from core.sandbox.executor import run_sandboxed

from .._categories import SkillCategory
from .._registry import SkillSpec, register


def run_command(command: str, cwd: str = ".", timeout: int = 120) -> dict:
    result = run_sandboxed(command, cwd=cwd, timeout=timeout)
    return {
        "cmd": result.cmd,
        "returncode": result.returncode,
        "success": result.success,
        "output": result.output,
        "timed_out": result.timed_out,
    }


try:
    register(SkillSpec(
        "terminal.run",
        "Run command",
        "Run a project command through the sandbox policy.",
        SkillCategory.TERMINAL,
        tags=("terminal", "sandbox"),
        callable=run_command,
    ))
except ValueError:
    pass


__all__ = ["run_command"]
