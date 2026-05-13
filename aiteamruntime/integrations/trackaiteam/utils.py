from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext

from .model import model_meta, role_key

STREAM_EMIT_INTERVAL_SECONDS = 0.75
STREAM_EMIT_CHARS = 700
STREAM_EVENT_CAP = 1200


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
    if raw.startswith(".aiteamruntime/") or raw == ".aiteamruntime":
        return fallback
    return raw


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


class ModelTraceStreamer:
    def __init__(self, ctx: AgentContext, *, stage: str, operation: str, role_key: str, work_item_id: str = "") -> None:
        self.ctx = ctx
        self.stage = stage
        self.operation = operation
        self.role_key = role_key
        self.work_item_id = work_item_id
        self._buffers = {"reasoning": "", "content": ""}
        self._last_emit = time.monotonic()

    def __call__(self, payload: dict[str, Any]) -> None:
        event_type = str(payload.get("type") or "")
        if event_type in {"reasoning", "content"}:
            self._buffers[event_type] += str(payload.get("text") or "")
            if self._should_emit(event_type):
                self._emit(event_type)
            return
        if event_type == "done":
            self.flush()

    def _should_emit(self, event_type: str) -> bool:
        if len(self._buffers[event_type]) >= STREAM_EMIT_CHARS:
            return True
        return (time.monotonic() - self._last_emit) >= STREAM_EMIT_INTERVAL_SECONDS

    def _emit(self, event_type: str) -> None:
        text = self._buffers[event_type]
        if not text:
            return
        self._buffers[event_type] = ""
        self._last_emit = time.monotonic()
        preview = text[-STREAM_EVENT_CAP:]
        self.ctx.emit(
            "reasoning" if event_type == "reasoning" else "progress",
            {
                "stream": event_type,
                "operation": self.operation,
                "delta": preview,
                "chars": len(text),
                "truncated": len(text) > len(preview),
                **model_meta(self.role_key),
            },
            stage=self.stage,
            work_item_id=self.work_item_id,
            role_state="running",
        )

    def flush(self) -> None:
        self._emit("reasoning")
        self._emit("content")


def write_workspace_text(ctx: AgentContext, path: str, content: str) -> Path:
    full_path = ctx.runtime.resources.resolve_workspace_path(ctx.run_id, path)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return full_path


def artifact_rel_path(ctx: AgentContext, name: str, *, project_dir: str = "") -> str:
    safe_run = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in ctx.run_id)[:80] or "run"
    safe_name = Path(str(name or "artifact.md")).name
    project = str(project_dir or "").replace("\\", "/").strip("/")
    if project.startswith(".aiteamruntime/"):
        project = project.split("/", 1)[1]
    safe_project = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in project)[:80].strip("-")
    parts = ["runs", safe_run, "artifacts"]
    if safe_project:
        parts.append(safe_project)
    parts.append(safe_name)
    return "/".join(parts)


def write_run_artifact(ctx: AgentContext, name: str, content: str, *, project_dir: str = "") -> tuple[str, Path, str]:
    rel_path = artifact_rel_path(ctx, name, project_dir=project_dir)
    full_path = (ctx.runtime.store.root / rel_path).resolve()
    store_root = ctx.runtime.store.root.resolve()
    full_path.relative_to(store_root)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    ref_id = ctx.ref_file(str(full_path), content=content, metadata={"artifact": name, "project_dir": project_dir})
    return str(full_path), full_path, ref_id


def tool_file_path(plan: dict[str, Any]) -> str:
    files = plan.get("files") if isinstance(plan.get("files"), list) else []
    if files:
        parent = Path(files[0]).parent.as_posix()
        return f"{parent}/tools.md" if parent and parent != "." else ".aiteamruntime/tools.md"
    return ".aiteamruntime/tools.md"
