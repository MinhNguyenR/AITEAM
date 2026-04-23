from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from core.config import config


def get_cache_root() -> Path:
    root = config.cache_root
    root.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        try:
            os.chmod(root, 0o700)
        except OSError:
            pass
    return root


def _safe_join(root: Path, *parts: str) -> Path:
    candidate = (root.joinpath(*parts)).resolve()
    base = root.resolve()
    if not candidate.is_relative_to(base):
        raise ValueError(f"Path escapes cache root: {candidate}")
    return candidate


def path_under_cache(*parts: str) -> Path:
    return _safe_join(get_cache_root(), *parts)


def ensure_run_dir(task_uuid: str) -> Path:
    run_dir = path_under_cache("runs", task_uuid)
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def ensure_db_dir() -> Path:
    db_dir = path_under_cache("db")
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir


def ensure_workflow_dir() -> Path:
    workflow_dir = path_under_cache("workflow")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    return workflow_dir


def ensure_ask_data_dir() -> Path:
    ask_dir = path_under_cache("ask-data")
    ask_dir.mkdir(parents=True, exist_ok=True)
    return ask_dir


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    path = path.resolve()
    root = get_cache_root().resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Refuse to write outside cache root: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding=encoding) as f:
            f.write(text)
        os.replace(tmp_name, path)
    finally:
        try:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)
        except OSError:
            pass


@dataclass(frozen=True)
class TaskWorkspace:
    task_uuid: str
    run_dir: Path
    state_path: Path
    context_path: Path
    validation_report_path: Path


def paths_for_task(task_uuid: str) -> TaskWorkspace:
    from core.domain.delta_brief import CONTEXT_FILENAME, STATE_FILENAME, VALIDATION_REPORT_FILENAME

    run_dir = ensure_run_dir(task_uuid)
    return TaskWorkspace(
        task_uuid=task_uuid,
        run_dir=run_dir,
        state_path=run_dir / STATE_FILENAME,
        context_path=run_dir / CONTEXT_FILENAME,
        validation_report_path=run_dir / VALIDATION_REPORT_FILENAME,
    )


def latest_context_path() -> Path | None:
    runs_dir = path_under_cache("runs")
    if not runs_dir.exists():
        return None
    latest: tuple[float, Path] | None = None
    for run_dir in runs_dir.iterdir():
        if not run_dir.is_dir():
            continue
        ctx = run_dir / "context.md"
        if not ctx.is_file():
            continue
        mtime = ctx.stat().st_mtime
        if latest is None or mtime > latest[0]:
            latest = (mtime, ctx)
    return latest[1] if latest else None


__all__ = [
    "TaskWorkspace",
    "atomic_write_text",
    "ensure_ask_data_dir",
    "ensure_db_dir",
    "ensure_run_dir",
    "ensure_workflow_dir",
    "get_cache_root",
    "latest_context_path",
    "path_under_cache",
    "paths_for_task",
]
