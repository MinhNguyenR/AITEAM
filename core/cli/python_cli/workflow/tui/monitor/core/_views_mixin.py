"""Mixin: check-view and log-view open/close helpers."""
from __future__ import annotations

from ._utils import _r2a


class _ViewsMixin:

    # ── check view ────────────────────────────────────────────────────────────

    def _open_check(self, root: str) -> None:
        try:
            from core.cli.python_cli.features.context.flow import find_context_md, is_no_context
            ctx = find_context_md(root)
            if not ctx or is_no_context(ctx):
                self._write("[dim]✗ No context.md found[/dim]")
                return
            lines_raw: list[str] = []
            lines_raw.append(_r2a("[bold]── context.md ──────────────────────────────────[/bold]"))
            for line in ctx.read_text(encoding="utf-8").splitlines():
                safe = line.replace("[", r"\[")
                lines_raw.append(_r2a(safe))
            lines_raw.append(_r2a("[dim]─────────────────────────────────────────────────[/dim]"))
            lines_raw.append(_r2a(
                "[bold yellow]accept[/bold yellow] accept  ·  "
                "[bold red]delete[/bold red] reject  ·  "
                "[dim cyan]edit[/dim cyan] open editor  ·  "
                "[dim]q/Esc close[/dim]"
            ))
            self._check_lines    = lines_raw
            self._check_scroll   = 0
            self._check_ctx_path = str(ctx)
            self._check_edited   = False
            self._check_mode     = True
            if self._app:
                self._app.layout.focus(self._check_buffer)
                self._app.invalidate()
        except Exception as e:
            self._write(f"[red]✗ check error: {e}[/red]")

    def _close_check(self, *, silent: bool = False) -> None:
        self._check_mode  = False
        self._check_lines = []
        if not silent:
            self._write("[dim]    └──[/dim] [dim]context.md đã được mở[/dim]")
        if self._app:
            self._app.layout.focus(self._main_buffer)
            self._app.invalidate()

    # ── log view ──────────────────────────────────────────────────────────────

    def _open_log(self) -> None:
        try:
            from ....runtime.persist.activity_log import format_activity_lines, list_recent_activity
            lines_raw: list[str] = []
            lines_raw.append(_r2a("[bold]── activity log ───────────────────────────────────[/bold]"))
            records = list_recent_activity(limit=300)
            fmt_lines = format_activity_lines(records, "")
            if not fmt_lines:
                lines_raw.append(_r2a("[dim]  (no activity logged yet)[/dim]"))
            else:
                for line in fmt_lines:
                    lines_raw.append(_r2a(line))
            lines_raw.append(_r2a("[dim]──────────────────────────────────────────────────[/dim]"))
            lines_raw.append(_r2a("[dim]  Esc / q to go back[/dim]"))
            self._log_lines  = lines_raw
            self._log_scroll = 0
            self._log_mode   = True
            if self._app:
                self._app.invalidate()
        except Exception as e:
            self._write(f"[dim]  (log error: {e})[/dim]")

    def _close_log(self) -> None:
        self._log_mode  = False
        self._log_lines = []
        if self._app:
            self._app.invalidate()
