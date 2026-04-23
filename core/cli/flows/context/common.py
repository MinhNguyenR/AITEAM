from __future__ import annotations

from pathlib import Path

from core.cli.state import load_context_state, log_system_action, update_context_state
from core.cli.workflow.runtime import session as ws
from core.cli.workflow.runtime.activity_log import clear_workflow_activity_log
from core.config import config
from core.domain.delta_brief import STATE_FILENAME
from utils.file_manager import latest_context_path, paths_for_task
from utils.logger import log_state_json_deleted_on_accept


def graphrag_drop(context_path: Path) -> None:
    try:
        from core.storage.graphrag_store import delete_by_context_path

        delete_by_context_path(context_path)
    except ImportError:
        return
    except OSError:
        return


def find_context_md(project_root: str) -> Path | None:
    latest_ctx = latest_context_path()
    if latest_ctx and latest_ctx.exists():
        return latest_ctx
    candidates = [
        config.BASE_DIR / "context.md",
        config.BASE_DIR / "data" / "context.md",
        Path(project_root).parent / "test" / "context.md",
        Path(project_root).parent / "context.md",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def state_path_for_context(context_path: Path) -> Path | None:
    state = load_context_state()
    task_uuid = str(state.get("task_uuid") or "").strip()
    if task_uuid:
        return paths_for_task(task_uuid).state_path
    candidate = context_path.parent / STATE_FILENAME
    if candidate.exists():
        return candidate
    return None


def delete_state_json_on_accept(context_path: Path) -> None:
    sp = state_path_for_context(context_path)
    if not sp:
        return
    try:
        sp.unlink(missing_ok=True)
    except (ImportError, OSError, ValueError, TypeError):
        return
    log_state_json_deleted_on_accept(sp)


def delete_state_json_for_context(context_path: Path) -> None:
    sp = state_path_for_context(context_path)
    if not sp:
        return
    try:
        sp.unlink(missing_ok=True)
    except (OSError, ValueError, TypeError):
        return


def full_context_cleanup(context_path: Path, *, reason: str = "deleted") -> None:
    graphrag_drop(context_path)
    try:
        context_path.unlink(missing_ok=True)
    except OSError:
        pass
    delete_state_json_for_context(context_path)
    update_context_state(reason, context_path, reason=reason)
    log_system_action("context.delete", f"{context_path} reason={reason}")
    clear_workflow_activity_log()
    ws.reset_pipeline_visual()
    ws.set_paused_for_review(False)
    ws.set_should_finalize(False)


__all__ = [
    "graphrag_drop",
    "find_context_md",
    "state_path_for_context",
    "delete_state_json_on_accept",
    "delete_state_json_for_context",
    "full_context_cleanup",
]
