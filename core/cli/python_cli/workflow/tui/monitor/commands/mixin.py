"""Mixin: _handle_cmd dispatcher; sub-handlers live in command modules."""
from __future__ import annotations

from core.cli.python_cli.i18n import t

from ..core._constants import _GATE_ACCEPTED, _GATE_DECLINED, _GATE_REGEN, _GATE_WAITING
from .gate import handle_accept, handle_delete, handle_post_delete, handle_post_delete_clear
from .explainer import handle_explainer_inline as _handle_explainer_fn


class _CommandsMixin:
    def _handle_check_cmd(self, cmd: str) -> None:
        from .check import handle_check_cmd

        handle_check_cmd(self, cmd)

    def _handle_cmd(self, raw: str) -> None:
        from ....runtime import session as ws
        from ..helpers import _info_list_lines, _project_root_default

        raw = (raw or "").strip()
        root = _project_root_default()

        if self._log_mode:
            low = raw.lower()
            if low == "/exit":
                self._close_log()
                if self._app:
                    self._app.exit()
            elif low in ("q", "esc", "/back", ""):
                self._close_log()
            elif low.startswith("/open "):
                parts = raw.split(None, 1)
                self._open_log_file(parts[1] if len(parts) > 1 else "")
            elif low in ("/clear log", "/clear"):
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

        if self._clarif_mode:
            clarif = self._clarif_data
            q_list = clarif.get("q_list", [])
            idx = getattr(self, "_clarif_idx", 0)

            if raw == "/back" and idx > 0:
                self._clarif_idx -= 1
                if len(self._clarif_answers) > self._clarif_idx:
                    self._clarif_answers.pop()
                self._set_live("")
                if self._app:
                    self._app.invalidate()
                return

            if idx >= len(q_list):
                return

            current_q = q_list[idx]
            opts = current_q.get("options", [])
            answer: str | None = None

            if raw.isdigit():
                oidx = int(raw) - 1
                if 0 <= oidx < len(opts):
                    answer = f"Q: {current_q.get('question')} -> A: {t('clarify.option')} {raw} ({opts[oidx]})"
            elif raw == "/skip":
                if opts:
                    answer = f"Q: {current_q.get('question')} -> A: {t('clarify.option')} 1 ({opts[0]})"
                else:
                    answer = f"Q: {current_q.get('question')} -> A: __skip__"
            elif raw.startswith("/btw"):
                note = raw[4:].strip()
                if note:
                    answer = f"Q: {current_q.get('question')} -> A: {note}"

            if answer is not None:
                if not hasattr(self, "_clarif_answers"):
                    self._clarif_answers = []
                self._clarif_answers.append(answer)
                self._clarif_idx += 1

                if self._clarif_idx >= len(q_list):
                    self._clarif_mode = False
                    self._clarif_data = {}
                    self._set_live("")

                    final_answer_text = "\n".join(self._clarif_answers)
                    clarif_role = getattr(self, "_clarif_role", "") or t("pipeline.leader")
                    self._write(
                        f"[bold blue]INFO[/bold blue] [bold]{clarif_role}[/bold]  "
                        f"[dim]\"{t('clarify.answered').format(n=len(self._clarif_answers))}\"[/dim]  "
                        f"[green]OK[/green]"
                    )
                    try:
                        ws.answer_clarification(final_answer_text)
                    except Exception:
                        pass
                else:
                    self._set_live("")
                    if self._app:
                        self._app.invalidate()
                return

        if raw.startswith("/ask"):
            if self._ask_thinking:
                self._write(f"[dim]x {t('cmd.ask_busy')}[/dim]")
                return
            text = raw[4:].strip()
            if not text:
                self._write(f"[dim]x {t('cmd.ask_usage')}[/dim]")
                return
            self._do_new_task(text, "ask", root)
            return

        if raw.startswith("/agent"):
            if self._ask_thinking:
                self._write(f"[dim]x {t('cmd.ask_busy')}[/dim]")
                return
            text = raw[6:].strip()
            if not text:
                self._write(f"[dim]x {t('cmd.agent_usage')}[/dim]")
                return
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", "") or snap.get("paused_at_gate"):
                self._queue_task(text, "agent")
                return
            self._do_new_task(text, "agent", root)
            return

        if raw.startswith("/btw"):
            rest_btw = raw[4:].strip()
            if not rest_btw:
                self._write(f"[dim]x {t('cmd.btw_empty')}[/dim]")
                return
            snap_btw = ws.get_pipeline_snapshot()
            if str(snap_btw.get("active_step") or "idle") in ("idle", "end_failed", ""):
                self._write(f"[dim]x {t('cmd.btw_idle')}[/dim]")
                return
            self._handle_btw_inline(rest_btw, snap_btw)
            return

        if raw.startswith("/explainer"):
            rest_exp = raw[len("/explainer"):].strip()
            if not rest_exp:
                self._write("[yellow]Chưa có file chỉ định. Dùng /explainer @file path/to/file.py[/yellow]")
                return
            self._handle_explainer_inline(rest_exp, root)
            return

        if raw.startswith("/restore"):
            rest_restore = raw[len("/restore"):].strip()
            task_text = ("restore " + rest_restore).strip()
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", ""):
                self._queue_task(task_text, "agent")
                return
            self._do_new_task(task_text, "agent", root)
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
                item = self._clarif_data.get("q_list", [])[self._clarif_idx]
                q = item.get("question", "")
                opts = item.get("options", []) or []
                self._clarif_mode = False
                self._clarif_data = {}
                self._set_live("")
                default_answer = opts[0] if opts else t("btw.skipped")
                clarif_role = getattr(self, "_clarif_role", "") or t("pipeline.leader")
                self._write(
                    f"[bold blue]INFO[/bold blue] [bold]{clarif_role}[/bold]  [dim]\"{q[:60]}\"[/dim]  "
                    f"[dim]->  {default_answer}[/dim] [green]OK[/green]"
                )
                try:
                    ws.answer_clarification(
                        f"Q: {q} -> A: {t('clarify.option')} 1 ({opts[0]})" if opts else "__skip__"
                    )
                except Exception:
                    pass
            else:
                self._write(f"[dim]x {t('cmd.skip_no_clarif')}[/dim]")
            return

        if raw.startswith("/clear"):
            snap_c = ws.get_pipeline_snapshot()
            active_c = str(snap_c.get("active_step") or "idle")
            if active_c not in ("idle", "end_failed", ""):
                self._write(f"[dim]x {t('cmd.clear_running')}[/dim]")
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
            handle_accept(self, root, ws)
            return

        if raw.lower() == "/delete":
            handle_delete(self, root, ws)
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
            task_parts = rest_t.rsplit(None, 1)
            if len(task_parts) == 2 and task_parts[1].lower() in ("ask", "agent"):
                task_text, task_mode = task_parts[0].strip(), task_parts[1].lower()
            else:
                task_text, task_mode = rest_t, "agent"
            if str(snap.get("active_step") or "idle") not in ("idle",):
                self._queue_task(task_text, task_mode)
                return
            self._do_new_task(task_text, task_mode, root)
            return

        if raw.lower() in ("/exit", "/quit", "/q", "/back"):
            if self._app:
                self._app.exit()
            return

        if raw.startswith("/") and len(raw) > 1:
            self._write(f"[dim]x {t('cmd.invalid_cmd').format(cmd=raw.split()[0])}[/dim]")
            return

        if self._exit_confirm_mode:
            self._exit_confirm_mode = False
            if raw.lower() in ("y", "yes"):
                self._do_cleanup_exit()
            else:
                self._write(f"[dim]  {t('ui.cancelled')}[/dim]")
            return

        if self._post_delete_mode:
            handle_post_delete(self, raw, root, ws)
            return

        if getattr(self, "_post_delete_clear_mode", False):
            handle_post_delete_clear(self, raw)
            return

        if not raw:
            snap_e = ws.get_pipeline_snapshot()
            active_e = str(snap_e.get("active_step") or "idle")
            if active_e not in ("idle", "end_failed", "") or self._ask_thinking:
                self._write(f"[dim]{t('cmd.running_hint').format(step=active_e)}[/dim]", indent=True)
            else:
                self._write(f"[dim]  {t('cmd.idle_tip')}[/dim]", indent=True)
            return

        parts = raw.split(None, 1)
        cmd = parts[0].lower()

        try:
            from core.app_state import log_system_action

            log_system_action("monitor.input", raw[:300])
        except Exception:
            pass

        if cmd in ("exit", "quit", "q", "back"):
            self._write(f"[dim]{t('cmd.slash_required').format(cmd='/' + cmd)}[/dim]")
            return

        if cmd in ("check", "accept", "delete", "log", "task", "info", "btw", "skip", "clear", "ask", "agent"):
            self._write(f"[dim]{t('cmd.slash_required').format(cmd='/' + cmd)}[/dim]")
            return

        snap_now = ws.get_pipeline_snapshot()
        active_now = str(snap_now.get("active_step") or "idle")
        if active_now not in ("idle", "end_failed", ""):
            self._write(f"[dim]  {t('cmd.btw_note_hint')}[/dim]")
            return
        if self._ask_thinking:
            self._write(f"[dim]x {t('cmd.ask_busy')}[/dim]")
            return
        self._handle_ask_inline(raw)

    def _handle_ask_inline(self, question: str) -> None:
        from .ask import handle_ask_inline

        handle_ask_inline(self, question)

    def _handle_btw_inline(self, msg: str, snap: dict) -> None:
        from .btw import handle_btw_inline

        handle_btw_inline(self, msg, snap)

    def _handle_explainer_inline(self, payload: str, root: str) -> None:
        _handle_explainer_fn(self, payload, root)
