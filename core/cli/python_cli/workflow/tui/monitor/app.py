"""WorkflowListApp -- assembles all mixins into the runnable TUI."""
from __future__ import annotations

import asyncio
import queue
import sys
import time
from typing import Optional

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer

from .core._constants import _GATE_WAITING
from .core._content_mixin import _ContentMixin
from .core._views_mixin import _ViewsMixin
from .core._render_mixin import _RenderMixin
from .commands.mixin import _CommandsMixin
from .core._tasks_mixin import _TasksMixin
from .core._layout_mixin import _LayoutMixin
from core.cli.python_cli.i18n import t


class WorkflowListApp(
    _ContentMixin,
    _ViewsMixin,
    _RenderMixin,
    _CommandsMixin,
    _TasksMixin,
    _LayoutMixin,
):
    """prompt_toolkit TUI for the AI workflow pipeline.

    Layout:
      hint bar  (1 line)
      -----------------
      content   (scrollable history + live step)
      -----------------
      hints bar (1 line)
      -> input   (1 line)
    """

    def __init__(self) -> None:
        # Display state
        self._history_raw:    list[str]            = []
        self._live_raw:       str                  = ""
        self._hint_raw:       str                  = ""
        self._spin:           int                  = 0
        self._scroll_offset:  int                  = 0

        # Pipeline tracking
        self._seen_activity_min_ts: Optional[float] = None
        self._last_active_step:     str             = ""
        self._shown_file_events:    list            = []
        self._token_warned:         bool            = False
        self._seen_running:         bool            = False
        self._pipeline_pending:     bool            = False

        # Inline mode flags
        self._post_delete_mode:  bool           = False
        self._exit_confirm_mode: bool           = False
        self._last_ctrl_c_ts:    float          = 0.0
        self._task_mode_pending: Optional[str]  = None
        self._last_task_text:    str            = ""
        self._attempt_count:     int            = 1
        self._gate_state:        str            = _GATE_WAITING

        # Check-view
        self._check_mode:         bool       = False
        self._check_lines:        list[str]  = []
        self._check_scroll:       int        = 0
        self._check_ctx_path:     str        = ""
        self._check_auto_refresh: bool       = False
        self._check_edited:       bool       = False

        # Ask / clarification
        self._ask_thinking: bool = False
        self._clarif_mode:  bool = False
        self._clarif_data:  dict = {}

        # Ambassador completion guard (fast-path)
        self._last_ambassador_status: str  = ""
        self._ambassador_done_written: bool = False

        # Completed node set (for /info green dots)
        self._completed_nodes: set[str] = set()

        # Log-view
        self._log_mode:   bool      = False
        self._log_lines:  list[str] = []
        self._log_scroll: int       = 0

        # Leader stream accumulator (per-tick, capped at 12k chars for display)
        self._stream_acc: str = ""

        # Leader substate: "idle" | "reading" | "generating"
        self._leader_substate: str = "idle"
        self._leader_reading_file: str = "state.json"

        # Tool Curator substate tracking ("" | reading | thinking | looking_for | writing)
        self._curator_substate:    str   = ""
        self._curator_substate_at: float = 0.0
        self._curator_started_at:  float = 0.0
        self._curator_detail:      str   = ""

        # Ambassador substate tracking ("" | reading | thinking | writing)
        self._ambassador_substate: str = ""
        self._ambassador_detail:   str = ""

        # Leader session substate from leader.py explicit calls
        self._leader_session_substate: str = ""
        self._leader_session_detail:   str = ""

        # Previous completed step display (ANSI) -- prepended to live section
        self._prev_step_display: str = ""

        # Reasoning/thinking stream
        self._reasoning_acc:    str  = ""
        self._reasoning_active: bool = False

        # Cached line count for fast mouse scroll
        self._cached_display_count: int = 0

        self._cmd_q:           queue.Queue           = queue.Queue()
        self._app:             Optional[Application] = None
        self._main_buffer:     Optional[Buffer]      = None
        self._check_buffer:    Optional[Buffer]      = None

        # Command palette popup
        self._autocomplete_active: bool = False
        self._autocomplete_items:  list = []
        self._gate_pending:        bool = False
        self._paste_collapse_used: bool = False
        self._pasted_payload:      str  = ""
        self._pasted_placeholder:  str  = ""
        self._queued_tasks:        list[tuple[str, str]] = []

    # -- async tick ------------------------------------------------------------

    async def _tick_loop(self) -> None:
        from ...runtime import session as ws

        while True:
            await asyncio.sleep(0.25)
            try:
                self._spin += 1

                # Auto-refresh check content when editor is open
                if self._check_mode and self._check_auto_refresh:
                    try:
                        from .helpers import _project_root_default
                        from core.cli.python_cli.features.context import find_context_md
                        from ..core._utils import _r2a
                        ctx = find_context_md(_project_root_default())
                        if ctx and ctx.exists():
                            lines_raw = [_r2a(f"[bold]-- context.md --[/bold]  [dim]{ctx}[/dim]")]
                            from core.cli.python_cli.shell.safe_read import safe_read_text
                            for line in safe_read_text(ctx).splitlines():
                                safe = line.replace("[", r"\[")
                                lines_raw.append(_r2a(safe))

                            accept_label = t('context.accept_desc').split(' -- ')[0].lower()
                            delete_label = t('context.delete_desc').split(' -- ')[0].lower()
                            edit_label   = t('context.edit_desc').split(' -- ')[0].lower()
                            back_label   = t('nav.back').split(' ')[0]

                            lines_raw.append(_r2a(f"[dim]{accept_label}  .  {delete_label}  .  {edit_label}  .  q {back_label}[/dim]"))
                            self._check_lines = lines_raw
                    except Exception:
                        pass

                # Auto-select clarification after 30s of no response
                if (self._clarif_mode
                        and hasattr(self, "_clarif_start")
                        and (time.time() - self._clarif_start) > 360):
                    _ac       = self._clarif_data
                    _opts     = _ac.get("options", [])
                    _auto_ans = f"{t('clarify.option')} 1: {_opts[0]}" if _opts else "__skip__"
                    _cq       = _ac.get("question", "")
                    self._clarif_mode = False
                    self._clarif_data = {}
                    self._set_live("")
                    _ans_d = t("btw.skipped") if _auto_ans == "__skip__" else _auto_ans[:60]
                    self._write(
                        f"[bold blue]*[/bold blue] [bold]{t('pipeline.leader')}[/bold]  [dim]\"{_cq[:60]}\"[/dim]"
                        f"  [dim]->  {_ans_d}[/dim] [green]OK[/green]"
                    )
                    self._write(f"[dim]{t('clarify.auto_skip')}[/dim]")
                    try:
                        ws.answer_clarification(_auto_ans)
                    except Exception:
                        pass

                # Drain command queue -- each command is isolated so one failure won't kill the loop
                while not self._cmd_q.empty():
                    try:
                        raw = self._cmd_q.get_nowait()
                    except queue.Empty:
                        break
                    try:
                        if raw.startswith("__check__:"):
                            self._handle_check_cmd(raw[10:])
                        else:
                            self._handle_cmd(raw)
                    except Exception as _cmd_exc:
                        try:
                            self._write(f"[bold red]ERR {t('ui.error')} {t('ui.choice').lower()}:[/bold red] {_cmd_exc}")
                        except Exception:
                            pass

                # Auto-exit when pipeline finishes
                snap   = ws.get_pipeline_snapshot()
                active = str(snap.get("active_step") or "idle")
                if active not in ("idle", "end_failed", "") or snap.get("ambassador_status") == "running":
                    self._seen_running   = True
                    self._pipeline_pending = False
                if ((self._seen_running or self._pipeline_pending) and snap.get("run_finished")
                        and not snap.get("paused_at_gate")
                        and self._gate_state == _GATE_WAITING):
                    if snap.get("graph_failed"):
                        self._write("")
                        self._write(f"[bold red]ERR[/bold red] [bold]{t('pipeline.failed')}[/bold] -- {time.strftime('%H:%M:%S')}")
                        err_msg = snap.get("status_message") or ""
                        # These are markers, but we should also check localized versions if they were pushed to status
                        _ok_msgs = {
                            "Dang chay LangGraph pipeline...",
                            "Ambassador parsing task...",
                            "Pipeline hoan tat",
                            "Currently running LangGraph pipeline...",
                            "Pipeline complete",
                            t("pipeline.complete"),
                            ""
                        }
                        if err_msg and err_msg not in _ok_msgs:
                            err_safe = err_msg[:160].replace("[", r"\[")
                            self._write(f"[dim red]  {err_safe}[/dim red]")
                        self._write(f"[dim]  {t('pipeline.fail_hint')}[/dim]")
                        self._set_live("")
                        self._scroll_offset = 0
                    elif ws.get_pipeline_redirect() == "ask":
                        # Ambassador redirected to ask -- do NOT print Pipeline complete
                        ws.set_pipeline_redirect(None)
                        self._write(f"[dim]  {t('pipeline.ask_redirect')}[/dim]")
                        self._set_live("")
                        self._handle_ask_inline(self._last_task_text)
                    else:
                        self._flush_final(snap)
                    self._seen_running     = False
                    self._pipeline_pending = False
                    try:
                        ws.set_pipeline_run_finished(False)
                        ws.reset_pipeline_visual()
                    except Exception:
                        pass
                    try:
                        from .helpers import _project_root_default
                        self._start_next_queued_task(_project_root_default())
                    except Exception:
                        pass

            except Exception:
                pass

            # Always refresh display -- isolated so body errors can't skip it
            try:
                self._refresh()
                if self._app:
                    self._app.invalidate()
            except Exception as _ref_exc:
                _ref_msg = str(_ref_exc)
                if getattr(self, "_last_refresh_err", "") != _ref_msg:
                    self._last_refresh_err = _ref_msg
                    try:
                        self._history_raw.append(
                            f"\x1b[31m[{t('ui.error').lower()}] {_ref_msg}\x1b[0m"
                        )
                        if self._app:
                            self._app.invalidate()
                    except Exception:
                        pass

    # -- entry point -----------------------------------------------------------

    def run(self) -> None:
        from ...runtime import session as ws

        self._replay_history()
        _snap_init = ws.get_pipeline_snapshot()

        # Reset stale run_finished from previous session so /info starts clean
        _active_now = str(_snap_init.get("active_step") or "idle")
        _amb_now    = str(_snap_init.get("ambassador_status") or "idle")
        _is_live    = (_active_now not in ("idle", "end_failed", "")
                       or _amb_now == "running")
        if _snap_init.get("run_finished") and not _is_live:
            try:
                ws.set_pipeline_run_finished(False)
                ws.reset_pipeline_visual()
            except Exception:
                pass
            _snap_init = ws.get_pipeline_snapshot()
            _amb_now   = str(_snap_init.get("ambassador_status") or "idle")

        _amb_init = _amb_now
        self._last_ambassador_status = _amb_init
        if _amb_init == "done":
            self._ambassador_done_written = True
            self._completed_nodes.add("ambassador")

        if _is_live:
            self._seen_running = True
            self._set_live(
                f"[bold yellow]*[/bold yellow] [dim]{t('pipeline.reconnecting')} -- [bold]{_active_now.replace('_', ' ')}[/bold][/dim]"
            )

        self._app = self._build_app()

        async def _main():
            task = asyncio.create_task(self._tick_loop())
            try:
                await self._app.run_async()
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        try:
            asyncio.run(_main())
        finally:
            sys.stdout.write("\033[?25h\033[0m")
            sys.stdout.flush()


__all__ = ["WorkflowListApp"]
