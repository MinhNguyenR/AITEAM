from __future__ import annotations

from core.cli.python_cli.features.context.common import (
    delete_state_json_on_accept,
    find_context_md,
    full_context_cleanup,
    graphrag_drop,
)
from core.app_state import log_system_action, update_context_state
from core.runtime import session as ws
from core.cli.python_cli.workflow.runtime.persist.activity_log import clear_workflow_activity_log
from core.cli.python_cli.workflow.runtime.graph.runner import resume_workflow
from core.domain.delta_brief import is_no_context


def apply_context_accept_from_monitor(project_root: str) -> bool:
    ctx = find_context_md(project_root)
    if not ctx or is_no_context(ctx):
        return False
    delete_state_json_on_accept(ctx)
    update_context_state("completed", ctx, reason="accept_from_monitor")
    log_system_action("context.accept_monitor", str(ctx))
    if ws.is_paused_for_review():
        ws.set_should_finalize(True)
        ws.set_context_accept_status("accepted")
        result = resume_workflow()
        # Delete context.md AFTER resume so tool_curator can read it during pipeline execution.
        # Deleting before resume caused apply_stale_workflow_ui_if_needed() to reset active_step
        # to "idle" on every poll tick while nodes were running.
        try:
            graphrag_drop(ctx)
            ctx.unlink(missing_ok=True)
        except OSError:
            pass
        return bool(result)
    try:
        graphrag_drop(ctx)
        ctx.unlink(missing_ok=True)
    except OSError:
        pass
    return True


def apply_context_back_from_monitor(project_root: str) -> None:
    ctx = find_context_md(project_root)
    if ctx:
        update_context_state("active", ctx, reason="review_deferred_monitor")
        log_system_action("context.review.back_monitor", str(ctx))
    if ws.is_paused_for_review():
        ws.set_should_finalize(False)
        ws.set_context_accept_status("deferred")
        ws.set_pipeline_paused_at_gate(True)
        ws.set_phase_paused_gate()


def apply_context_delete_from_monitor(project_root: str) -> bool:
    ctx = find_context_md(project_root)
    if not ctx:
        return False
    full_context_cleanup(ctx, reason="delete_from_monitor")
    return True


def apply_context_prepare_regenerate(project_root: str) -> None:
    ctx = find_context_md(project_root)
    if ctx:
        full_context_cleanup(ctx, reason="regenerate_from_monitor_prep")
    else:
        if ws.is_paused_for_review():
            ws.set_paused_for_review(False)
        clear_workflow_activity_log()
        ws.reset_pipeline_visual()


__all__ = [
    "apply_context_accept_from_monitor",
    "apply_context_back_from_monitor",
    "apply_context_delete_from_monitor",
    "apply_context_prepare_regenerate",
]
