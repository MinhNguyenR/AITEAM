"""Mixin: task dispatch, countdown, cleanup, exit helpers."""
from __future__ import annotations

import threading
import time

from ._constants import _GATE_WAITING, _GATE_REGEN, _SPINNER


class _TasksMixin:
    def _queue_task(self, task_text: str, task_mode: str) -> None:
        self._queued_tasks.append((task_text, task_mode))
        idx = len(self._queued_tasks)
        preview = " ".join(str(task_text or "").split())
        if len(preview) > 96:
            preview = preview[:93] + "..."
        self._write("")
        self._write(f"[bold yellow]QUEUE[/bold yellow] [bold]Task #{idx}[/bold]  [dim]{time.strftime('%H:%M:%S')}[/dim]")
        self._write(f"[on #2a2a2a]  {preview}  [/on #2a2a2a]")
        self._scroll_offset = 0
        if self._app:
            self._app.invalidate()

    def _start_next_queued_task(self, root: str) -> bool:
        if not self._queued_tasks:
            return False
        task_text, task_mode = self._queued_tasks.pop(0)
        remaining = len(self._queued_tasks)
        self._write("")
        self._write(f"[bold yellow]QUEUE[/bold yellow] [bold]Starting next task[/bold]  [dim]{remaining} queued[/dim]")
        self._do_new_task(task_text, task_mode, root)
        return True

    def _do_new_task(self, task_text: str, task_mode: str, root: str) -> None:
        from ....runtime import session as ws
        self._last_task_text  = task_text
        self._attempt_count   = 1
        self._gate_state      = _GATE_WAITING
        self._scroll_offset   = 0
        self._leader_substate = "idle"
        self._clarif_history  = []
        self._clarif_mode     = False
        self._clarif_data     = {}

        if task_mode == "ask":
            self._handle_ask_inline(task_text)
            return

        self._write("")
        self._write(f"[bold cyan]*[/bold cyan] [bold]Task[/bold]  [dim]{time.strftime('%H:%M:%S')}[/dim]")
        _tw, _tc, _tls = task_text.split(), "", []
        for _w in _tw:
            if len(_tc) + len(_w) + 1 > 100:
                if _tc: _tls.append(_tc)
                _tc = _w
            else:
                _tc = (_tc + " " + _w).strip()
        if _tc: _tls.append(_tc)
        for _tl in _tls[:12]:
            self._write(f"[on #2a2a2a]  {_tl}  [/on #2a2a2a]")

        ws.reset_pipeline_visual()
        ws.set_pipeline_run_finished(False)
        self._last_active_step        = ""
        self._shown_file_events       = []
        self._ambassador_done_written = False
        self._last_ambassador_status  = ""
        self._completed_nodes.clear()
        self._reasoning_acc           = ""
        self._reasoning_active        = False
        self._prev_step_display       = ""
        from core.cli.python_cli.features.start.flow import start_pipeline_from_tui
        start_pipeline_from_tui(task_text, root, task_mode)
        self._pipeline_pending = True

    def _start_decline_countdown(self) -> None:
        self._write("[dim]  Clearing in 3...[/dim]")

        def _run() -> None:
            for r in (2, 1, 0):
                time.sleep(1.0)
                def _upd(r=r):
                    self._write(f"[dim]  Clearing in {r}...[/dim]")
                    if self._app: self._app.invalidate()
                self._safe_ui(_upd)

            def _clear():
                from ....runtime import session as ws
                self._history_raw.clear()
                self._set_live("")
                self._scroll_offset     = 0
                self._last_active_step  = ""
                self._shown_file_events = []
                self._gate_state        = _GATE_WAITING
                self._seen_running      = False
                self._pipeline_pending  = False
                self._leader_substate   = "idle"
                self._prev_step_display = ""
                try:
                    ws.clear_stream_history()
                except Exception:
                    pass
                ws.reset_pipeline_visual()
                if self._app: self._app.invalidate()

            self._safe_ui(_clear)

        threading.Thread(target=_run, daemon=True).start()

    def _ask_exit_inline(self) -> None:
        self._exit_confirm_mode = True
        self._write("")
        self._write("[bold yellow]![/bold yellow] Workflow running -- Exit & cleanup? [bold](y/n)[/bold]")
        self._scroll_offset = 0

    def _do_cleanup_exit(self) -> None:
        from ....runtime import session as ws
        from ..helpers import _project_root_default
        self._write("[dim]  Stopping pipeline...[/dim]")
        try:
            ws.request_pipeline_stop()
        except Exception:
            pass
        try:
            from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
            apply_context_delete_from_monitor(_project_root_default())
        except Exception:
            pass
        ws.reset_pipeline_visual()
        if self._app:
            self._app.exit()
