"""Mixin: _refresh, _render_live, _on_step_transition, _flush_final."""
from __future__ import annotations

import time

from core.cli.python_cli.i18n import t

from ._constants import (
    _GEN_STEPS, _SPINNER, _ACTION, _ACTION_DONE,
    _GATE_WAITING, _GATE_ACCEPTED, _GATE_DECLINED, _GATE_REGEN,
)
from ._utils import _get_role_display, _r2a


def _get_done_markup(node: str, role: str, tok: str, st: dict = None) -> str:
    from ..state import render_ambassador_done, render_curator_done
    from ..state._leader import render_leader_tree
    if node == "ambassador":
        return render_ambassador_done(role, tok)
    elif node == "leader_generate" and st:
        st['is_done'] = True
        return render_leader_tree("[bold green]●[/bold green]", role, st)
    elif node == "tool_curator":
        return render_curator_done(role, tok)
    return ""


class _RenderMixin:

    def _refresh(self) -> None:
        from ....runtime import session as ws
        from ..helpers import (
            TOKEN_WARN_THRESHOLD,
            _activity_min_ts_kw,
            _parse_file_events,
            _parse_token_counts,
            _parse_token_counts_for_node,
            _project_root_default,
        )

        ws.prune_stale_pipeline_notifications()
        ws.apply_stale_workflow_ui_if_needed(_project_root_default())

        snap   = ws.get_pipeline_snapshot()
        tier   = snap.get("brief_tier")
        toast  = str(snap.get("toast") or "")
        active = str(snap.get("active_step") or "idle")

        redir = ws.get_pipeline_redirect()
        if redir == "ask":
            return

        # Drain leader stream buffer
        new_chunk = ws.drain_leader_stream_buffer()
        if new_chunk:
            self._stream_acc = (self._stream_acc + new_chunk)[-12_000:]
        elif active not in _GEN_STEPS:
            self._stream_acc = ""
        buf = self._stream_acc

        # Drain reasoning buffer
        try:
            new_reasoning, r_is_active, r_just_ended = ws.drain_reasoning_buffer()
        except Exception:
            new_reasoning, r_is_active, r_just_ended = "", False, False
        if new_reasoning:
            self._reasoning_acc = (self._reasoning_acc + new_reasoning)[-12_000:]
        if r_just_ended:
            r_tok = len(self._reasoning_acc) // 4
            tok_r = f"  [dim]({r_tok:,} {t('unit.tokens')})[/dim]" if r_tok else ""
            self._write(f"[bold green]●[/bold green] {t('unit.reasoning').title()} {t('gate.accepted').lower()}{tok_r}")
            self._reasoning_acc = ""
        if not r_is_active and not new_reasoning and not r_just_ended and active not in _GEN_STEPS:
            self._reasoning_acc = ""
        self._reasoning_active = r_is_active

        # Activity min_ts reset
        mt = _activity_min_ts_kw() or 0.0
        if self._seen_activity_min_ts is None:
            self._seen_activity_min_ts = mt
        elif mt > self._seen_activity_min_ts + 1e-9:
            self._seen_activity_min_ts = mt
            self._last_active_step  = ""
            self._shown_file_events = []
            self._token_warned      = False

        pt, ct = _parse_token_counts()
        if (pt + ct) > TOKEN_WARN_THRESHOLD and not self._token_warned:
            self._token_warned = True
            self._write(f"[bold yellow]⚠ {t('dash.budget_title')}: {pt+ct:,} / 262k[/bold yellow]")

        # Gate pending flag for command palette
        self._gate_pending = (
            active == "human_context_gate"
            and self._gate_state not in (_GATE_ACCEPTED, _GATE_DECLINED, _GATE_REGEN)
        )

        # Hint bar
        sc  = _SPINNER[self._spin % len(_SPINNER)]
        tok = f"  in:{pt:,} out:{ct:,}" if (pt or ct) else ""
        running = active not in ("idle", "end_failed", "")
        adisp = f"\x1b[90m{sc}\x1b[0m \x1b[33m{active}\x1b[0m" if running else f"\x1b[2m{active}\x1b[0m"
        tp    = f"\x1b[33m{toast}\x1b[0m  " if toast.strip() else ""
        self._hint_raw = (
            f"{tp}\x1b[34mlist\x1b[0m  {adisp}  {t('info.tier')} {tier or '—'}"
            + (f"\x1b[2m{tok}\x1b[0m" if tok else "")
        )



        # Ambassador fast-path: ambassador completes before appearing as active_step
        ambasdr_status = str(snap.get("ambassador_status") or "idle")
        if (ambasdr_status == "done"
                and not self._ambassador_done_written
                and self._last_ambassador_status != "done"):
            self._ambassador_done_written = True
            self._completed_nodes.add("ambassador")
            pt_a, ct_a = _parse_token_counts_for_node("ambassador")
            tok_a = f"  [dim](in:{pt_a:,} out:{ct_a:,})[/dim]" if (pt_a or ct_a) else ""
            self._write("")
            from ..state import render_ambassador_done
            self._write(render_ambassador_done(_get_role_display("ambassador"), tok_a))
            self._last_active_step = "ambassador"
        self._last_ambassador_status = ambasdr_status

        # Step transitions
        if active != self._last_active_step:
            self._on_step_transition(self._last_active_step, active)
            self._last_active_step = active

        # Clarification gate — short-circuit live rendering
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
                    "total": len(q_list)
                }
            else:
                clarif_view = {"question": t("ui.loading"), "options": []}
                
            self._render_clarification(clarif_view)
            return
        elif getattr(self, "_clarif_mode", False) and not (clarif and clarif.get("pending")):
            self._clarif_mode = False
            self._clarif_data = {}
            self._clarif_idx = 0
            self._clarif_answers = []
            self._set_live("")

        # Per-role tokens
        node_pt, node_ct = (_parse_token_counts_for_node(active)
                            if active in _GEN_STEPS else (0, 0))
        if active in _GEN_STEPS and not (node_pt or node_ct):
            try:
                node_pt = ws.get_stream_prompt_tokens()
                node_ct = ws.get_stream_completion_tokens()
            except Exception:
                node_ct = len(buf) // 4 if buf else 0

        # Pull curator substate from session every tick
        try:
            cs = ws.get_curator_substate()
            self._curator_substate    = str(cs.get("substate") or "")
            self._curator_detail      = str(cs.get("detail") or "")
            self._curator_substate_at = float(cs.get("substate_at") or 0.0)
            self._curator_started_at  = float(cs.get("started_at") or 0.0)
        except Exception:
            pass

        # Substate logic for Leader reading -> generating transition
        if active == "leader_generate":
            # Wait for first completion token (buf or node_ct) to indicate LLM TTFT is done
            if (buf or node_ct) and getattr(self, "_leader_substate", "idle") == "reading":
                self._leader_substate = "generating"
                self._leader_read_elapsed = int(time.time() - getattr(self, "_leader_substate_start", time.time()))
                self._leader_substate_start = time.time()

        self._render_live(active, buf, node_pt, node_ct, snap)

        # Removed persistent _prev_step_display logic

        file_evs = _parse_file_events()
        if file_evs:
            self._shown_file_events = file_evs

    def _on_step_transition(self, prev: str, active: str) -> None:
        from ..helpers import _parse_token_counts_for_node

        pt, ct = _parse_token_counts_for_node(prev) if prev in _GEN_STEPS else (0, 0)

        if prev in _GEN_STEPS:
            role       = _get_role_display(prev)
            done_action = _ACTION_DONE.get(prev, _ACTION.get(prev, prev))
            tok        = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""

            _skip_header = (prev == "ambassador" and self._ambassador_done_written)
            if prev == "ambassador":
                self._ambassador_done_written = True
            self._completed_nodes.add(prev)

            if not _skip_header:
                self._write("")
                st = None
                if prev == "leader_generate":
                    st = self._build_leader_state(prev, "", pt, ct)
                done_markup = _get_done_markup(prev, role, tok, st)
                if done_markup:
                    self._write(done_markup)
                else:
                    self._write(f"[bold green]●[/bold green] [bold]{role}[/bold]  {done_action}{tok}")

            # Leader done logic
            if prev == "leader_generate":
                self._leader_substate   = "idle"

        if not hasattr(self, "_state_start_times"):
            self._state_start_times = {}
        self._state_start_times[active] = time.time()

        if active == "leader_generate" and prev != "leader_generate":
            self._leader_substate = "reading"
            self._leader_substate_start = time.time()
            self._leader_reading_file = "state.json"

        if active == "tool_curator" and prev != "tool_curator":
            self._curator_substate    = "reading"
            self._curator_started_at  = time.time()
            self._curator_substate_at = time.time()

        if prev == "tool_curator" and active != "tool_curator":
            self._completed_nodes.add("tool_curator")

        if prev == "human_context_gate" and active not in ("human_context_gate",):
            self._completed_nodes.add("human_context_gate")
            if self._gate_state == _GATE_ACCEPTED:
                from ..state import render_gate_accepted
                self._write("")
                self._write(render_gate_accepted())

        if active == "finalize_phase1":
            self._completed_nodes.add("finalize_phase1")

        if active in _GEN_STEPS or active in ("human_context_gate", "finalize_phase1"):
            self._write("")

        if active == "human_context_gate" and prev != "human_context_gate":
            self._write(f"[bold green]●[/bold green] [bold]context.md[/bold]  [dim]{t('pipeline.gen_context').lower()} — {time.strftime('%H:%M:%S')}[/dim]  [dim][bold]/check[/bold] {t('nav.choose').lower()} · [bold]/accept[/bold] · [bold]/delete[/bold][/dim]")
            self._scroll_offset = 0

    def _build_leader_state(self, active: str, buf: str, pt: int, ct: int) -> dict:
        substate = getattr(self, "_leader_substate", "idle")
        return {
            "substate":         substate,
            "read_elapsed":     getattr(self, "_leader_read_elapsed", 0) if substate != "reading" else 0,
            "read_pt":          pt,
            "reasoning_acc":    getattr(self, "_reasoning_acc", ""),
            "reasoning_active": getattr(self, "_reasoning_active", False),
            "buf":     buf,
            "pt":      pt,
            "ct":      ct,
            "attempt": getattr(self, "_attempt_count", 1),
            "is_done": False,
        }

    def _render_live(
        self, active: str, buf: str, pt: int, ct: int, snap: dict
    ) -> None:
        from ..state import (
            render_ambassador_running,
            render_leader_regen_starting,
            render_gate_waiting, render_gate_checking, render_gate_editing,
            render_gate_accepted, render_gate_declined,
            render_finalizing, render_transitional, render_idle, render_unknown,
        )
        from ..state._leader import render_leader_tree
        from ..state._tool_curator import render_curator_tree
        sc   = _SPINNER[self._spin % len(_SPINNER)]
        role = _get_role_display(active)

        # Gate declined: y/n prompt in live section only
        if self._gate_state == _GATE_DECLINED:
            self._set_live(render_gate_declined(sc))
            return

        # Idle / transitional
        if active in ("idle", "", "end_failed"):
            if self._gate_state == _GATE_REGEN:
                # Pipeline restarting for regen — attribute to leader
                self._set_live(render_leader_regen_starting(
                    sc, _get_role_display("leader_generate"), self._attempt_count
                ))
                return
            if (snap.get("ambassador_status") == "done"
                    and snap.get("brief_tier")
                    and not snap.get("run_finished")
                    and not snap.get("graph_failed")
                    and (self._seen_running or self._pipeline_pending)):
                self._set_live(render_transitional(sc))
            else:
                self._set_live(render_idle())
            return

        # Calculate elapsed
        if not hasattr(self, "_state_start_times"):
            self._state_start_times = {}
        elapsed = 0
        if active == "ambassador":
            elapsed = int(time.time() - self._state_start_times.get("ambassador", time.time()))
        elif active == "leader_generate":
            elapsed = int(time.time() - getattr(self, "_leader_substate_start", time.time()))

        # Ambassador running
        if active == "ambassador":
            self._set_live(render_ambassador_running(
                sc, role, buf, pt, ct, self._attempt_count, elapsed,
                reasoning_acc=self._reasoning_acc,
                reasoning_active=self._reasoning_active,
            ))
            return

        # Leader
        if active == "leader_generate":
            st = self._build_leader_state(active, buf, pt, ct)
            self._set_live(render_leader_tree(sc, role, st, elapsed))
            return

        # Human gate
        if active == "human_context_gate":
            if self._gate_state == _GATE_ACCEPTED:
                self._set_live(render_gate_accepted())
            elif self._check_mode and self._check_auto_refresh:
                self._set_live(render_gate_editing(sc))
            elif self._check_mode:
                self._set_live(render_gate_checking(sc))
            else:
                self._set_live(render_gate_waiting(sc))
            return

        # Tool Curator
        if active == "tool_curator":
            elapsed_c = int(time.time() - (self._curator_started_at or time.time()))
            st = {
                "substate": self._curator_substate or "reading",
                "detail":   self._curator_detail,
                "pt":       pt,
                "ct":       ct,
                "is_done":  False,
            }
            self._set_live(render_curator_tree(sc, role, st, elapsed_c))
            return

        # Finalize
        if active == "finalize_phase1":
            self._set_live(render_finalizing(sc))
            return

        self._set_live(render_unknown(sc, active))

    def _flush_final(self, snap: dict) -> None:
        from ..helpers import _parse_token_counts, _parse_file_events
        pt, ct   = _parse_token_counts()
        tok      = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
        file_evs = _parse_file_events()
        self._shown_file_events = file_evs
        self._completed_nodes.update(
            {"ambassador", "leader_generate", "human_context_gate",
             "tool_curator", "finalize_phase1"}
        )
        self._write("")
        self._write(f"[bold green]●[/bold green] [bold]{t('pipeline.complete')}[/bold] — {time.strftime('%H:%M:%S')}{tok}")
        self._set_live("")
        self._prev_step_display = ""
        self._scroll_offset = 0

    def _render_clarification(self, clarif: dict) -> None:
        from ..state._clarify import render_pending
        sc        = _SPINNER[self._spin % len(_SPINNER)]
        elapsed_c = int(time.time() - getattr(self, "_clarif_start", time.time()))
        role      = _get_role_display("leader_generate")
        # Clarification is completely standalone — not inside any leader branch
        self._set_live(render_pending(sc, clarif, elapsed_c, role))
