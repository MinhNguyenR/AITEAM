"""Mixin: _handle_cmd dispatcher; sub-handlers live in _commands_*.py modules."""
from __future__ import annotations

import threading

from ..core._constants import (
    _GATE_ACCEPTED, _GATE_DECLINED, _GATE_WAITING, _GATE_REGEN,
)
from core.cli.python_cli.i18n import t


class _CommandsMixin:

    def _handle_check_cmd(self, cmd: str) -> None:
        from .check import handle_check_cmd
        handle_check_cmd(self, cmd)

    # ── main command handler ──────────────────────────────────────────────────

    def _handle_cmd(self, raw: str) -> None:
        from ....runtime import session as ws
        from ..helpers import _project_root_default, _info_list_lines
        raw  = (raw or "").strip()
        root = _project_root_default()

        if self._log_mode:
            if raw.lower() == "exit":
                self._close_log()
                if self._app:
                    self._app.exit()
            elif raw.lower() in ("q", "quit", "close", "back", ""):
                self._close_log()
            elif raw.lower() in ("clear log", "clear"):
                try:
                    from ....runtime.persist.activity_log import clear_activity_log
                    clear_activity_log()
                except Exception:
                    pass
                from ..core._utils import _r2a
                self._log_lines = [_r2a(f"[dim]  ({t('cmd.log_cleared')})[/dim]")]
                self._log_scroll = 0
                if self._app:
                    self._app.invalidate()
            return

        if self._task_mode_pending is not None:
            mode = self._task_mode_pending
            self._task_mode_pending = None
            if not raw:
                self._write(f"[dim]  {t('cmd.no_task')}[/dim]")
                return
            self._do_new_task(raw, mode, root)
            return

        # Clarification response
        if self._clarif_mode:
            clarif = self._clarif_data
            q_list = clarif.get("q_list", [])
            idx    = getattr(self, "_clarif_idx", 0)
            
            if raw in ("/back", "back") and idx > 0:
                self._clarif_idx -= 1
                if len(self._clarif_answers) > self._clarif_idx:
                    self._clarif_answers.pop()
                self._set_live("")
                if self._app: self._app.invalidate()
                return

            if idx >= len(q_list):
                return # Should not happen, waiting for sync

            current_q = q_list[idx]
            opts   = current_q.get("options", [])
            answer: str | None = None

            if raw.isdigit():
                oidx = int(raw) - 1
                if 0 <= oidx < len(opts):
                    answer = f"Q: {current_q.get('question')} -> A: {t('clarify.option')} {raw} ({opts[oidx]})"
            elif raw in ("/skip", "skip"):
                answer = f"Q: {current_q.get('question')} -> A: __skip__"

            if answer is not None:
                if not hasattr(self, "_clarif_answers"):
                    self._clarif_answers = []
                self._clarif_answers.append(answer)
                self._clarif_idx += 1
                
                # If we've answered all questions
                if self._clarif_idx >= len(q_list):
                    self._clarif_mode = False
                    self._clarif_data = {}
                    self._set_live("")
                    
                    final_answer_text = "\n".join(self._clarif_answers)
                    self._write(
                        f"[bold blue]INFO[/bold blue] [bold]Leader[/bold]  [dim]\"{t('clarify.answered').format(n=len(self._clarif_answers))}\"[/dim]"
                        f"  [green]OK[/green]"
                    )
                    try:
                        ws.answer_clarification(final_answer_text)
                    except Exception:
                        pass
                else:
                    # Still more questions, just refresh UI
                    self._set_live("")
                    if self._app: self._app.invalidate()
                return

        if raw.startswith("/ask"):
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", ""):
                self._write(f"[dim]✗ {t('cmd.ask_pipeline_busy')}[/dim]")
                return
            if self._ask_thinking:
                self._write(f"[dim]✗ {t('cmd.ask_busy')}[/dim]")
                return
            text = raw[4:].strip()
            if not text:
                self._write(f"[dim]✗ {t('cmd.ask_usage')}[/dim]")
                return
            self._do_new_task(text, "ask", root)
            return

        if raw.startswith("/agent"):
            if self._ask_thinking:
                self._write(f"[dim]✗ {t('cmd.ask_busy')}[/dim]")
                return
            text = raw[6:].strip()
            if not text:
                self._write(f"[dim]✗ {t('cmd.agent_usage')}[/dim]")
                return
            self._do_new_task(text, "agent", root)
            return

        if raw.startswith("/btw"):
            rest_btw = raw[4:].strip()
            if not rest_btw:
                self._write(f"[dim]✗ {t('cmd.btw_empty')}[/dim]")
                return
            snap_btw = ws.get_pipeline_snapshot()
            if str(snap_btw.get("active_step") or "idle") in ("idle", "end_failed", ""):
                self._write(f"[dim]✗ {t('cmd.btw_idle')}[/dim]")
                return
            self._handle_btw_inline(rest_btw, snap_btw)
            return

        if raw.startswith("/info"):
            try:
                snap_info = ws.get_pipeline_snapshot()
                self._write("")
                for line in _info_list_lines(snap_info, self._spin, self._completed_nodes):
                    self._write(line)
            except Exception as e_info:
                self._write(f"[dim]  (info: {e_info})[/dim]")
            self._scroll_offset = 0
            return

        if raw.startswith("/skip"):
            if self._clarif_mode:
                q = self._clarif_data.get("q_list", [])[self._clarif_idx].get("question", "")
                self._clarif_mode = False
                self._clarif_data = {}
                self._set_live("")
                _ans_d = t("btw.skipped")
                self._write(
                    f"[bold blue]INFO[/bold blue] [bold]{t('pipeline.leader')}[/bold]  [dim]\"{q[:60]}\"[/dim]"
                    f"  [dim]→  {_ans_d}[/dim] [green]OK[/green]"
                )
                try:
                    ws.answer_clarification("__skip__")
                except Exception:
                    pass
            else:
                self._write(f"[dim]✗ {t('cmd.skip_no_clarif')}[/dim]")
            return

        if raw.startswith("/clear"):
            _snap_c = ws.get_pipeline_snapshot()
            _active_c = str(_snap_c.get("active_step") or "idle")
            if _active_c not in ("idle", "end_failed", ""):
                self._write(f"[dim]✗ {t('cmd.clear_running')}[/dim]")
                return
            rest_c = raw[6:].strip()
            if rest_c == "all":
                self._history_raw.clear()
                self._set_live("")
                self._prev_step_display = ""
                return
            if rest_c.lower().startswith("text"):
                self._write(f"[dim]  {t('cmd.clear_text_hint')}[/dim]")
                return
            self._write(f"[dim]  {t('cmd.clear_hint')}[/dim]")
            return

        if raw.lower().startswith("/check"):
            self._open_check(root)
            return

        if raw.lower() == "/accept":
            snap = ws.get_pipeline_snapshot()
            if not snap.get("paused_at_gate"):
                self._write(f"[dim]✗ {t('cmd.no_gate')}[/dim]")
                return
            self._gate_state = _GATE_ACCEPTED
            self._write("")
            self._write(f"[bold green]GATE[/bold green] [bold]Human Gate[/bold]  [bold green]OK: {t('context.accepted')}[/bold green]")
            self._scroll_offset = 0
            def _accept_bg():
                try:
                    from core.cli.python_cli.features.context.monitor_actions import apply_context_accept_from_monitor
                    apply_context_accept_from_monitor(root)
                except Exception:
                    pass
            threading.Thread(target=_accept_bg, daemon=True).start()
            return

        if raw.lower() == "/delete":
            try:
                from core.cli.python_cli.features.context.monitor_actions import apply_context_delete_from_monitor
                apply_context_delete_from_monitor(root)
                self._gate_state       = _GATE_DECLINED
                self._post_delete_mode = True
                self._scroll_offset    = 0
            except Exception as e:
                self._write(f"[red]✗ {t('context.delete_error').format(e=e)}[/red]")
            return

        if raw.lower().startswith("/log"):
            self._open_log()
            return

        if raw.lower().startswith("/task"):
            rest_t = raw[5:].strip()
            if not rest_t:
                self._write(f"[dim]  {t('cmd.task_usage')}[/dim]")
                return
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle",):
                self._write(f"[dim]✗ {t('cmd.task_running')}[/dim]")
                return
            task_parts = rest_t.rsplit(None, 1)
            if len(task_parts) == 2 and task_parts[1].lower() in ("ask", "agent"):
                task_text, task_mode = task_parts[0].strip(), task_parts[1].lower()
            else:
                task_text, task_mode = rest_t, "agent"
            self._do_new_task(task_text, task_mode, root)
            return

        if raw.lower() in ("/exit", "/quit", "/q", "/back"):
            try:
                ws.request_pipeline_stop()
            except Exception:
                pass
            if self._app:
                self._app.exit()
            return

        if raw.startswith("/") and len(raw) > 1:
            self._write(f"[dim]✗ {t('cmd.invalid_cmd').format(cmd=raw.split()[0])}[/dim]")
            return

        if self._exit_confirm_mode:
            self._exit_confirm_mode = False
            if raw.lower() in ("y", "yes"):
                self._do_cleanup_exit()
            else:
                self._write(f"[dim]  {t('ui.cancelled')}[/dim]")
            return

        if self._post_delete_mode:
            self._post_delete_mode = False
            if not raw or raw.lower() in ("n", "no"):
                self._write(f"[dim]      SKIP[/dim] {t('del.no_regen')}")
                self._write(f"[dim]      SKIP[/dim] {t('del.clear_prompt')}")
                self._post_delete_clear_mode = True
            elif raw.lower() in ("y", "yes"):
                self._attempt_count += 1
                self._clarif_history = []
                self._gate_state        = _GATE_REGEN
                self._last_active_step  = ""
                self._shown_file_events = []
                self._leader_substate   = "idle"
                self._completed_nodes.discard("leader_generate")
                self._completed_nodes.discard("human_context_gate")
                self._completed_nodes.discard("finalize_phase1")
                self._write(f"[dim]      REG[/dim] [cyan]{t('del.regenerating').format(n=self._attempt_count)}[/cyan]")
                if self._last_task_text:
                    ws.reset_pipeline_visual()
                    ws.set_pipeline_run_finished(False)
                    from core.cli.python_cli.features.start.flow import start_pipeline_from_tui
                    start_pipeline_from_tui(self._last_task_text, root, "agent", regenerate=True)
                    self._pipeline_pending = True
                else:
                    self._write(f"[dim]  {t('del.no_prev_task')}[/dim]")
            else:
                self._do_new_task(raw, "agent", root)
            return

        if getattr(self, "_post_delete_clear_mode", False):
            self._post_delete_clear_mode = False
            if raw.lower() in ("y", "yes"):
                self._write(f"[dim]      DEL[/dim] [dim]{t('ui.clearing')}[/dim]")
                self._gate_state = _GATE_WAITING
                self._start_decline_countdown()
            else:
                self._write(f"[dim]      KEEP[/dim] [dim]{t('del.keep_state')}[/dim]")
                self._gate_state = _GATE_DECLINED
            return

        if not raw:
            snap_e   = ws.get_pipeline_snapshot()
            active_e = str(snap_e.get("active_step") or "idle")
            if active_e not in ("idle", "end_failed", "") or self._ask_thinking:
                self._write(f"[dim]{t('cmd.running_hint').format(step=active_e)}[/dim]", indent=True)
            else:
                self._write(f"[dim]  {t('cmd.idle_tip')}[/dim]", indent=True)
            return

        parts = raw.split(None, 1)
        cmd   = parts[0].lower()
        rest  = parts[1].strip() if len(parts) > 1 else ""

        try:
            from core.cli.python_cli.shell.state import log_system_action
            log_system_action("monitor.input", raw[:300])
        except Exception:
            pass

        if cmd in ("exit", "quit", "q", "back"):
            try:
                ws.request_pipeline_stop()
            except Exception:
                pass
            if self._app:
                self._app.exit()
            return

        if cmd in ("check", "accept", "delete", "log", "task", "info", "btw"):
            self._write(f"[dim]💡 {t('cmd.slash_required').format(cmd=raw.strip())}[/dim]")
            return

        # Plain text → inline ask when pipeline is idle
        snap_now   = ws.get_pipeline_snapshot()
        active_now = str(snap_now.get("active_step") or "idle")
        if active_now not in ("idle", "end_failed", ""):
            self._write(f"[dim]  {t('cmd.btw_note_hint')}[/dim]")
            return
        if self._ask_thinking:
            self._write(f"[dim]✗ {t('cmd.ask_busy')}[/dim]")
            return
        self._handle_ask_inline(raw)

    def _handle_ask_inline(self, question: str) -> None:
        from .ask import handle_ask_inline
        handle_ask_inline(self, question)

    def _handle_btw_inline(self, msg: str, snap: dict) -> None:
        from .btw import handle_btw_inline
        handle_btw_inline(self, msg, snap)
