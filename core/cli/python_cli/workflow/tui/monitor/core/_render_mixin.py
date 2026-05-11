"""Mixin: monitor refresh and live rendering."""
from __future__ import annotations

import time

from core.cli.python_cli.i18n import t

from ._constants import (
    _GATE_ACCEPTED,
    _GATE_DECLINED,
    _GATE_REGEN,
    _GEN_STEPS,
    _SPINNER,
)
from ._refresh_state_mixin import _RefreshStateMixin
from ._role_card_mixin import _RoleCardMixin
from ._transition_mixin import _TransitionMixin
from ._utils import _get_role_display


class _RenderMixin(_RefreshStateMixin, _RoleCardMixin, _TransitionMixin):
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

        snap = ws.get_pipeline_snapshot()
        tier = snap.get("brief_tier")
        toast = str(snap.get("toast") or "")
        active = str(snap.get("active_step") or "idle")

        if ws.get_pipeline_redirect() == "ask":
            return

        buf = self._drain_stream_buffers(ws, active)

        self._reset_activity_window_if_needed(_activity_min_ts_kw() or 0.0)
        pt, ct = _parse_token_counts()
        self._update_token_warning(pt, ct, TOKEN_WARN_THRESHOLD)
        self._update_gate_pending(active)
        self._update_hint_bar(ws, active, tier, toast, pt, ct)

        self._write_ambassador_fast_done(ws, snap, _parse_token_counts_for_node)

        if active != self._last_active_step:
            self._on_step_transition(self._last_active_step, active)
            self._last_active_step = active

        if self._handle_clarification(ws, active):
            return

        node_pt, node_ct = self._node_token_counts(ws, active, buf, _parse_token_counts_for_node)
        self._pull_role_substates(ws)
        self._update_leader_stream_substate(active, buf, node_ct)
        self._drain_update_diffs(ws)

        self._render_live(active, buf, node_pt, node_ct, snap)

        file_evs = _parse_file_events()
        if file_evs:
            self._shown_file_events = file_evs

    def _render_live(
        self, active: str, buf: str, pt: int, ct: int, snap: dict
    ) -> None:
        from ..state import (
            render_ambassador_running,
            render_finalizing,
            render_gate_accepted,
            render_gate_checking,
            render_gate_declined,
            render_gate_editing,
            render_gate_waiting,
            render_idle,
            render_leader_regen_starting,
            render_transitional,
            render_unknown,
        )
        from ..state._leader import render_leader_tree
        from ..state._tool_curator import render_curator_tree

        sc = _SPINNER[self._spin % len(_SPINNER)]
        role = _get_role_display(active)

        if self._gate_state == _GATE_DECLINED:
            self._set_live(render_gate_declined(sc))
            return

        role_cards = self._render_active_role_cards(active, sc, buf, snap)
        if role_cards and active not in ("human_context_gate", "finalize_phase1"):
            self._set_live(role_cards)
            return

        if active in ("idle", "", "end_failed"):
            if self._gate_state == _GATE_REGEN:
                self._set_live(render_leader_regen_starting(
                    sc, _get_role_display("leader_generate"), self._attempt_count
                ))
                return
            if (
                snap.get("ambassador_status") == "done"
                and snap.get("brief_tier")
                and not snap.get("run_finished")
                and not snap.get("graph_failed")
                and (self._seen_running or self._pipeline_pending)
            ):
                self._set_live(render_transitional(sc))
            else:
                self._set_live(render_idle())
            return

        elapsed = 0
        if not hasattr(self, "_state_start_times"):
            self._state_start_times = {}
        if active == "ambassador":
            elapsed = int(time.time() - self._state_start_times.get("ambassador", time.time()))
        elif active == "leader_generate":
            elapsed = int(time.time() - getattr(self, "_leader_substate_start", time.time()))

        if active == "ambassador":
            self._set_live(render_ambassador_running(
                sc,
                role,
                buf,
                pt,
                ct,
                self._attempt_count,
                elapsed,
                reasoning_acc=self._reasoning_acc,
                reasoning_active=self._reasoning_active,
                substate=getattr(self, "_ambassador_substate", ""),
                detail=getattr(self, "_ambassador_detail", ""),
            ))
            return

        if active == "leader_generate":
            st = self._build_leader_state(active, buf, pt, ct)
            self._set_live(render_leader_tree(sc, role, st, elapsed))
            return

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

        if active == "tool_curator":
            elapsed_c = int(time.time() - (self._curator_started_at or time.time()))
            st = {
                "substate": self._curator_substate or "reading",
                "detail": self._curator_detail,
                "pt": pt,
                "ct": ct,
                "buf": buf,
                "is_done": False,
            }
            self._set_live(render_curator_tree(sc, role, st, elapsed_c))
            return

        if active in ("worker", "restore_worker"):
            from ..state._worker import render_worker_tree

            elapsed_w = int(time.time() - self._state_start_times.get("worker", time.time()))
            st = {
                "substate": getattr(self, "_worker_substate", "") or "reading",
                "detail": getattr(self, "_worker_detail", ""),
                "reading_files": getattr(self, "_worker_reading_files", []),
                "using_cmd": getattr(self, "_worker_using_cmd", ""),
                "pt": pt,
                "ct": ct,
                "buf": buf,
                "is_done": False,
            }
            self._set_live(render_worker_tree(sc, role, st, elapsed_w))
            return

        if active == "secretary":
            from ..state._secretary import render_secretary_tree

            elapsed_s = int(time.time() - self._state_start_times.get("secretary", time.time()))
            st = {
                "substate": getattr(self, "_secretary_substate", "") or "asking",
                "detail": getattr(self, "_secretary_detail", ""),
                "command_results": getattr(self, "_secretary_commands", []),
                "is_done": False,
            }
            self._set_live(render_secretary_tree(sc, role, st, elapsed_s))
            return

        if active == "finalize_phase1":
            self._set_live(render_finalizing(sc))
            return

        self._set_live(render_unknown(sc, active))

    def _flush_final(self, snap: dict) -> None:
        from ..helpers import _parse_file_events, _parse_token_counts

        pt, ct = _parse_token_counts()
        tok = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
        self._shown_file_events = _parse_file_events()
        self._completed_nodes.update(
            {
                "ambassador",
                "leader_generate",
                "human_context_gate",
                "tool_curator",
                "worker",
                "restore_worker",
                "secretary",
                "finalize_phase1",
            }
        )
        self._write("")
        self._write(f"[bold green]*[/bold green] [bold]{t('pipeline.complete')}[/bold] -- {time.strftime('%H:%M:%S')}{tok}")
        self._set_live("")
        self._prev_step_display = ""
        self._scroll_offset = 0

    def _render_clarification(self, clarif: dict) -> None:
        from ..state._clarify import render_pending

        sc = _SPINNER[self._spin % len(_SPINNER)]
        elapsed_c = int(time.time() - getattr(self, "_clarif_start", time.time()))
        role = getattr(self, "_clarif_role", "") or _get_role_display("leader_generate")
        self._set_live(render_pending(sc, clarif, elapsed_c, role))
