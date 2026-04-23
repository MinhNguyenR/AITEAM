"""Validate monitor command queue payloads (paths, prompt length)."""

from __future__ import annotations

from pathlib import Path

MAX_MONITOR_PROMPT_CHARS = 32_000


def is_path_under_base(path: Path, base: Path) -> bool:
    try:
        path.resolve().relative_to(base.resolve())
        return True
    except ValueError:
        return False


def resolve_trusted_project_root(
    raw: str | None,
    *,
    repo_root: str,
    home_config_dir: Path,
) -> Path | None:
    bases = [Path(repo_root).resolve(), Path.cwd().resolve(), home_config_dir.resolve()]
    if not raw or not str(raw).strip():
        return Path(repo_root).resolve()
    try:
        candidate = Path(raw).expanduser().resolve()
    except OSError:
        return None
    for b in bases:
        if is_path_under_base(candidate, b):
            return candidate
    return None


def sanitize_monitor_prompt(raw: str | None) -> str:
    p = (raw or "").strip()
    if len(p) > MAX_MONITOR_PROMPT_CHARS:
        return p[:MAX_MONITOR_PROMPT_CHARS]
    return p


__all__ = [
    "MAX_MONITOR_PROMPT_CHARS",
    "is_path_under_base",
    "resolve_trusted_project_root",
    "sanitize_monitor_prompt",
]
