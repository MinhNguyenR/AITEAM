"""Gate command handlers: /accept, /delete, post-delete flow."""
from __future__ import annotations

from ..core._constants import _GATE_ACCEPTED, _GATE_DECLINED, _GATE_REGEN, _GATE_WAITING
from .._task_pool import submit_monitor_task
from core.cli.python_cli.i18n import t


def handle_accept(app, root: str, ws) -> None:
    snap = ws.get_pipeline_snapshot()
    if not snap.get("paused_at_gate"):
        app._write(f"[dim]x {t('cmd.no_gate')}[/dim]")
        return
    app._gate_state = _GATE_ACCEPTED
    app._write("")
    app._write(
        f"[bold green]GATE[/bold green] [bold]Human Gate[/bold]  "
        f"[bold green]OK: {t('context.accepted')}[/bold green]"
    )
    app._scroll_offset = 0

    def _accept_bg() -> None:
        try:
            from core.cli.python_cli.features.context.monitor_actions import apply_context_accept_from_monitor
            apply_context_accept_from_monitor(root)
        except Exception:
            pass

    submit_monitor_task(_accept_bg)


def handle_delete(app, root: str, ws) -> None:
    try:
        from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
        apply_context_delete_from_monitor(root)
        app._gate_state = _GATE_DECLINED
        app._post_delete_mode = True
        app._scroll_offset = 0
    except Exception as e:
        app._write(f"[red]x {t('context.delete_error').format(e=e)}[/red]")


def handle_post_delete(app, raw: str, root: str, ws) -> None:
    app._post_delete_mode = False
    if not raw or raw.lower() in ("n", "no"):
        app._write(f"[dim]      SKIP[/dim] {t('del.no_regen')}")
        app._write(f"[dim]      {t('del.clear_prompt')}[/dim]")
        app._gate_state = _GATE_WAITING
        app._post_delete_clear_mode = True
        app._start_decline_countdown()
    elif raw.lower() in ("y", "yes"):
        app._attempt_count += 1
        app._clarif_history = []
        app._gate_state = _GATE_REGEN
        app._last_active_step = ""
        app._shown_file_events = []
        app._leader_substate = "idle"
        app._completed_nodes.discard("leader_generate")
        app._completed_nodes.discard("human_context_gate")
        app._completed_nodes.discard("finalize_phase1")
        if app._last_task_text:
            ws.reset_pipeline_visual()
            ws.set_pipeline_run_finished(False)
            from core.cli.python_cli.features.start.flow import start_pipeline_from_tui
            start_pipeline_from_tui(app._last_task_text, root, "agent", regenerate=True)
            app._pipeline_pending = True
        else:
            app._write(f"[dim]  {t('del.no_prev_task')}[/dim]")
    else:
        app._do_new_task(raw, "agent", root)


def handle_post_delete_clear(app, raw: str) -> None:
    app._post_delete_clear_mode = False
    if raw.lower() in ("y", "yes"):
        app._write(f"[dim]      DEL[/dim] [dim]{t('ui.clearing')}[/dim]")
        app._gate_state = _GATE_WAITING
        app._start_decline_countdown()
    else:
        app._write(f"[dim]      KEEP[/dim] [dim]{t('del.keep_state')}[/dim]")
        app._gate_state = _GATE_DECLINED
