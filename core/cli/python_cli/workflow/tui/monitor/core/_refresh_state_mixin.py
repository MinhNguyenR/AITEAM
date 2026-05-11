"""Mixin helpers for monitor refresh state collection."""
from __future__ import annotations

import time

from core.cli.python_cli.i18n import t

from ._constants import _GEN_STEPS, _SPINNER, _GATE_ACCEPTED, _GATE_DECLINED, _GATE_REGEN
from ._utils import _get_role_display


class _RefreshStateMixin:
    def _drain_stream_buffers(self, ws, active: str) -> str:
        new_chunk = ws.drain_leader_stream_buffer()
        if new_chunk:
            self._stream_acc = (self._stream_acc + new_chunk)[-50_000:]
        elif active not in _GEN_STEPS:
            self._stream_acc = ""

        try:
            new_reasoning, r_is_active, r_just_ended = ws.drain_reasoning_buffer()
        except Exception:
            new_reasoning, r_is_active, r_just_ended = "", False, False
        if new_reasoning:
            self._reasoning_acc = (self._reasoning_acc + new_reasoning)[-50_000:]
        if r_just_ended:
            r_tok = len(self._reasoning_acc) // 4
            tok_r = f"  [dim]({r_tok:,} {t('unit.tokens')})[/dim]" if r_tok else ""
            self._write(f"[bold green]*[/bold green] {t('unit.reasoning').title()} {t('gate.accepted').lower()}{tok_r}")
            self._reasoning_acc = ""
        if not r_is_active and not new_reasoning and not r_just_ended and active not in _GEN_STEPS:
            self._reasoning_acc = ""
        self._reasoning_active = r_is_active
        return self._stream_acc

    def _reset_activity_window_if_needed(self, min_ts: float) -> None:
        if self._seen_activity_min_ts is None:
            self._seen_activity_min_ts = min_ts
        elif min_ts > self._seen_activity_min_ts + 1e-9:
            self._seen_activity_min_ts = min_ts
            self._last_active_step = ""
            self._shown_file_events = []
            self._token_warned = False

    def _update_token_warning(self, prompt_tokens: int, completion_tokens: int, threshold: int) -> None:
        total = prompt_tokens + completion_tokens
        if total > threshold and not self._token_warned:
            self._token_warned = True
            self._write(f"[bold yellow]! {t('dash.budget_title')}: {total:,} / 262k[/bold yellow]")

    def _update_gate_pending(self, active: str) -> None:
        self._gate_pending = (
            active == "human_context_gate"
            and self._gate_state not in (_GATE_ACCEPTED, _GATE_DECLINED, _GATE_REGEN)
        )

    def _update_hint_bar(self, ws, active: str, tier: str | None, toast: str, prompt_tokens: int, completion_tokens: int) -> None:
        sc = _SPINNER[self._spin % len(_SPINNER)]
        if active in _GEN_STEPS:
            try:
                live_pt = ws.get_stream_prompt_tokens()
                live_ct = ws.get_stream_completion_tokens()
                tok = f"  in:{live_pt:,} out:{live_ct:,}" if (live_pt or live_ct) else ""
            except Exception:
                tok = f"  in:{prompt_tokens:,} out:{completion_tokens:,}" if (prompt_tokens or completion_tokens) else ""
        else:
            tok = f"  in:{prompt_tokens:,} out:{completion_tokens:,}" if (prompt_tokens or completion_tokens) else ""

        running = active not in ("idle", "end_failed", "")
        adisp = f"\x1b[90m{sc}\x1b[0m \x1b[33m{active}\x1b[0m" if running else f"\x1b[2m{active}\x1b[0m"
        tp = f"\x1b[33m{toast}\x1b[0m  " if toast.strip() else ""
        self._hint_raw = (
            f"{tp}\x1b[34mlist\x1b[0m  {adisp}  {t('info.tier')} {tier or '--'}"
            + (f"\x1b[2m{tok}\x1b[0m" if tok else "")
        )

    def _write_ambassador_fast_done(self, ws, snap: dict, parse_tokens_for_node) -> None:
        ambasdr_status = str(snap.get("ambassador_status") or "idle")
        if (
            ambasdr_status == "done"
            and not self._ambassador_done_written
            and self._last_ambassador_status != "done"
        ):
            self._ambassador_done_written = True
            self._completed_nodes.add("ambassador")
            pt_a, ct_a = parse_tokens_for_node("ambassador")
            tok_a = f"  [dim](in:{pt_a:,} out:{ct_a:,})[/dim]" if (pt_a or ct_a) else ""
            self._write("")
            from ..state import render_ambassador_done

            self._write(render_ambassador_done(_get_role_display("ambassador"), tok_a))
            self._last_active_step = "ambassador"
            try:
                ws.clear_ambassador_substate()
            except Exception:
                pass
        self._last_ambassador_status = ambasdr_status

    def _handle_clarification(self, ws, active: str) -> bool:
        clarif = None
        try:
            clarif = ws.get_clarification() if hasattr(ws, "get_clarification") else None
        except Exception:
            pass
        if clarif and clarif.get("pending"):
            if not getattr(self, "_clarif_mode", False):
                self._clarif_start = time.time()
                self._clarif_idx = 0
                self._clarif_answers = []
                self._clarif_role = _get_role_display(active if active not in ("idle", "") else "leader_generate")
            self._clarif_mode = True
            self._clarif_data = clarif

            q_list = clarif.get("q_list", [])
            idx = getattr(self, "_clarif_idx", 0)
            if idx < len(q_list):
                current_q = q_list[idx]
                clarif_view = {
                    "question": current_q.get("question", ""),
                    "options": current_q.get("options", []),
                    "current_idx": idx + 1,
                    "total": len(q_list),
                }
            else:
                clarif_view = {"question": t("ui.loading"), "options": []}
            self._render_clarification(clarif_view)
            return True

        if getattr(self, "_clarif_mode", False):
            self._clarif_mode = False
            self._clarif_data = {}
            self._clarif_idx = 0
            self._clarif_answers = []
            self._set_live("")
        return False

    def _node_token_counts(self, ws, active: str, buf: str, parse_tokens_for_node) -> tuple[int, int]:
        node_pt, node_ct = parse_tokens_for_node(active) if active in _GEN_STEPS else (0, 0)
        if active in _GEN_STEPS and not (node_pt or node_ct):
            try:
                node_pt = ws.get_stream_prompt_tokens()
                node_ct = ws.get_stream_completion_tokens()
            except Exception:
                node_ct = len(buf) // 4 if buf else 0
        return node_pt, node_ct

    def _pull_role_substates(self, ws) -> None:
        try:
            cs = ws.get_curator_substate()
            self._curator_substate = str(cs.get("substate") or "")
            self._curator_detail = str(cs.get("detail") or "")
            self._curator_substate_at = float(cs.get("substate_at") or 0.0)
            self._curator_started_at = float(cs.get("started_at") or 0.0)
        except Exception:
            pass

        try:
            self._workers_state = {}
            for worker_key in ("WORKER_A", "WORKER_B", "WORKER_C", "WORKER_D", "WORKER_E"):
                ws_s = ws.get_worker_substate(worker_key)
                self._workers_state[worker_key] = {
                    "substate": str(ws_s.get("substate") or ""),
                    "detail": str(ws_s.get("detail") or ""),
                    "reading_files": ws.get_worker_reading_files(worker_key),
                    "using_cmd": ws.get_worker_using_command(worker_key),
                }
            worker_key = getattr(self, "_worker_key", "WORKER_A")
            ws_s = ws.get_worker_substate(worker_key)
            self._worker_substate = str(ws_s.get("substate") or "")
            self._worker_detail = str(ws_s.get("detail") or "")
            self._worker_reading_files = ws.get_worker_reading_files(worker_key)
            self._worker_using_cmd = ws.get_worker_using_command(worker_key)
        except Exception:
            pass

        try:
            ss_ = ws.get_secretary_substate()
            self._secretary_substate = str(ss_.get("substate") or "")
            self._secretary_detail = str(ss_.get("detail") or "")
            self._secretary_commands = ws.get_secretary_command_results()
        except Exception:
            pass

        try:
            as_ = ws.get_ambassador_substate()
            self._ambassador_substate = str(as_.get("substate") or "")
            self._ambassador_detail = str(as_.get("detail") or "")
        except Exception:
            pass

        try:
            ls_ = ws.get_leader_substate()
            self._leader_session_substate = str(ls_.get("substate") or "")
            self._leader_session_detail = str(ls_.get("detail") or "")
        except Exception:
            pass

        try:
            es_ = ws.get_explainer_substate()
            self._explainer_substate = str(es_.get("substate") or "")
            self._explainer_detail = str(es_.get("detail") or "")
        except Exception:
            pass

    def _update_leader_stream_substate(self, active: str, buf: str, node_ct: int) -> None:
        if active != "leader_generate":
            return
        if (buf or node_ct) and getattr(self, "_leader_substate", "idle") == "reading":
            self._leader_substate = "generating"
            self._leader_read_elapsed = int(time.time() - getattr(self, "_leader_substate_start", time.time()))
            self._leader_substate_start = time.time()

    def _drain_update_diffs(self, ws) -> None:
        try:
            diffs = ws.pop_update_diffs()
            from ..state._update_state import render_create_block, render_update_block

            for diff in diffs:
                status = str(diff.get("status") or "UPDATE").upper()
                role = str(diff.get("role_name") or _get_role_display("worker"))
                self._write(render_create_block(role, diff) if status == "CREATE" else render_update_block(role, diff))
        except Exception:
            pass
