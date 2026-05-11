"""Command safety policy shared by Worker and Secretary."""

from __future__ import annotations

import re

# Destructive commands
_DESTRUCTIVE_RE = re.compile(
    r"rm\s+-rf|sudo\s+rm|mkfs|dd\s+if=|>\s*/dev/|chmod\s+777"
    r"|:\(\)\{|curl[^|]+\|\s*sh|wget[^|]+\|\s*sh|format\s+[a-z]:"
    r"|del\s+/[fsq]|rmdir\s+/[sq]|powershell\s+.*remove-item\s+.*-recurse",
    re.IGNORECASE,
)

# Shell injection / chaining metacharacters
_SHELL_INJECTION_RE = re.compile(
    r"&&|\|\||[;|`]|\$\(|>\s*\S|<\s*\S|>>|2>&",
)

_ALLOWED_PREFIXES = (
    "python", "py", "pytest", "pip", "uv", "npm", "pnpm", "yarn", "node",
    "npx",
    "git", "ruff", "mypy", "tsc", "echo", "dir", "ls", "where", "Get-ChildItem",
    "streamlit", "django-admin", "flask", "fastapi", "uvicorn", "cargo", "go",
    "dotnet", "java", "mvn", "gradle",
)


def is_command_safe(cmd: str) -> tuple[bool, str]:
    text = str(cmd or "").strip()
    if not text:
        return False, "empty command"
    if _SHELL_INJECTION_RE.search(text):
        return False, "shell chaining/redirection not allowed"
    if _DESTRUCTIVE_RE.search(text):
        return False, "matches destructive pattern"
    first = text.split()[0].strip().strip("&;")
    if first in _ALLOWED_PREFIXES:
        return True, "allowed prefix"
    # Allow common module invocations such as `python -m pytest`.
    if re.match(r"^(python|py)\s+-m\s+[A-Za-z0-9_.-]+", text):
        return True, "allowed python module"
    return False, f"command prefix not allowed: {first}"


__all__ = ["is_command_safe"]
