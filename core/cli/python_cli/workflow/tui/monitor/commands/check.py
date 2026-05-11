"""Check-view command handler."""
from __future__ import annotations

from core.cli.python_cli.i18n import t
from ..core._constants import _GATE_ACCEPTED, _GATE_DECLINED
from .._task_pool import submit_monitor_task


def handle_check_cmd(app, cmd: str) -> None:
    from ..core._utils import _r2a
    from ..helpers import _project_root_default

    root = _project_root_default()
    c = cmd.strip().lower()

    if c in ("/edit", "edit"):
        try:
            import subprocess
            from core.cli.python_cli.features.context import find_context_md
            from core.cli.python_cli.shell.safe_editor import build_editor_argv

            ctx = find_context_md(root)
            if not ctx:
                app._check_lines = [_r2a(f"[dim]ERR {t('cmd.check_no_ctx')}[/dim]")]
                if app._app:
                    app._app.invalidate()
                return
            subprocess.Popen(build_editor_argv(ctx))
            app._check_auto_refresh = True
            app._check_edited = True
        except Exception as e:
            app._check_lines = [_r2a(f"[red]ERR {t('cmd.edit_error').format(e=e)}[/red]")]
            if app._app:
                app._app.invalidate()
        return

    if c in ("/accept", "accept"):
        edited_note = f" ({t('ui.edited')})" if app._check_edited else ""
        app._close_check()
        app._write(f"[dim]        `--[/dim] [bold green]OK {t('gate.accepted_msg_short')}{edited_note}[/bold green]")
        app._gate_state = _GATE_ACCEPTED

        def _accept_bg():
            try:
                from core.cli.python_cli.features.context.monitor_actions import apply_context_accept_from_monitor
                apply_context_accept_from_monitor(root)
            except Exception:
                pass

        submit_monitor_task(_accept_bg)
        return

    if c in ("/delete", "delete"):
        edited_note = f" ({t('ui.edited')})" if app._check_edited else ""
        app._close_check()
        try:
            from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
            apply_context_delete_from_monitor(root)
            app._gate_state = _GATE_DECLINED
            app._post_delete_mode = True
            app._write(f"[dim]        `--[/dim] [red]ERR {t('gate.declined_msg_short')}{edited_note}[/red]")
        except Exception as e:
            app._write(f"[red]ERR {t('cmd.delete_failed_short').format(e=e)}[/red]")
        return

    if c in ("q", "quit", "close", "esc", "back", "/back", ""):
        app._close_check()
