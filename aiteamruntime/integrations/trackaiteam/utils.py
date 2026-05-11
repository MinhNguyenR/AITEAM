from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext

from .model import model_meta, role_key


def sleep(seconds: float) -> None:
    time.sleep(seconds)


def prompt(event: AgentEvent) -> str:
    return str(event.payload.get("prompt") or event.payload.get("task") or "")


def slug(value: str, fallback: str = "task") -> str:
    slugged = "".join(ch.lower() if ch.isalnum() else "-" for ch in value[:56]).strip("-")
    return "-".join(part for part in slugged.split("-") if part) or fallback


def safe_rel_path(path: str, fallback: str) -> str:
    raw = str(path or "").replace("\\", "/").strip()
    raw = raw.lstrip("/")
    invalid_windows_chars = set('<>:"|?*')
    if (
        not raw
        or raw.startswith("../")
        or "/../" in raw
        or raw == ".."
        or any(ch in invalid_windows_chars for ch in raw)
    ):
        return fallback
    if raw.startswith(".aiteamruntime/"):
        return raw
    return fallback


def model_error(ctx: AgentContext, *, stage: str, exc: Exception, work_item_id: str = "") -> None:
    resolved_role_key = role_key(ctx.agent_id)
    ctx.emit(
        "error",
        {"stage": stage, "type": type(exc).__name__, "message": str(exc), **model_meta(resolved_role_key)},
        status="error",
        stage=stage,
        work_item_id=work_item_id,
        role_state="error",
    )


def write_workspace_text(ctx: AgentContext, path: str, content: str) -> Path:
    full_path = ctx.runtime.resources.resolve_workspace_path(ctx.run_id, path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return full_path


def tool_file_path(plan: dict[str, Any]) -> str:
    files = plan.get("files") if isinstance(plan.get("files"), list) else []
    if files:
        parent = Path(files[0]).parent.as_posix()
        return f"{parent}/tools.md" if parent and parent != "." else ".aiteamruntime/tools.md"
    return ".aiteamruntime/tools.md"
