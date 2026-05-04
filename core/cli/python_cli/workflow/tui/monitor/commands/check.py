"""Check-view command handler (extracted from _commands_mixin)."""
from __future__ import annotations

import threading

from ..core._constants import _GATE_ACCEPTED, _GATE_DECLINED
from core.cli.python_cli.i18n import t


def handle_check_cmd(app, cmd: str) -> None:
    from ..helpers import _project_root_default
    from ..core._utils import _r2a

    root = _project_root_default()
    c = cmd.strip().lower()

    if c == "edit":
        try:
            from core.cli.python_cli.features.context import find_context_md
            from core.cli.python_cli.shell.safe_editor import build_editor_argv
            import subprocess
            ctx = find_context_md(root)
            if not ctx:
                app._check_lines = [_r2a(f"[dim]✗ {t('cmd.check_no_ctx')}[/dim]")]
                if app._app: app._app.invalidate()
                return
            subprocess.Popen(build_editor_argv(ctx))
            app._check_auto_refresh = True
            app._check_edited = True
        except Exception as e:
            app._check_lines = [_r2a(f"[red]✗ {t('cmd.edit_error').format(e=e)}[/red]")]
            if app._app: app._app.invalidate()
        return

    if c == "accept":
        edited_note = f" ({t('ui.edited')})" if app._check_edited else ""
        app._close_check()
        app._write(f"[dim]        └──[/dim] [bold green]✓ {t('gate.accepted_msg_short')}{edited_note}[/bold green]")
        app._gate_state = _GATE_ACCEPTED

        def _accept_bg():
            try:
                from core.cli.python_cli.features.context.monitor_actions import apply_context_accept_from_monitor
                apply_context_accept_from_monitor(root)
            except Exception:
                pass
        threading.Thread(target=_accept_bg, daemon=True).start()
        return

    if c == "delete":
        edited_note = f" ({t('ui.edited')})" if app._check_edited else ""
        app._close_check()
        try:
            from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
            apply_context_delete_from_monitor(root)
            app._gate_state       = _GATE_DECLINED
            app._post_delete_mode = True
            app._write(f"[dim]        └──[/dim] [red]✗ {t('gate.declined_msg_short')}{edited_note}[/red]")
        except Exception as e:
            app._write(f"[red]✗ {t('cmd.delete_failed_short').format(e=e)}[/red]")
        return

    if c in ("q", "quit", "close", "back", ""):
        app._close_check()
        return
