"""Mixin: _build_leader_state, _render_active_role_cards."""
from __future__ import annotations

import time
import sys

from ._constants import _GEN_STEPS, _SPINNER
from ._utils import _get_role_display


def _display_role(node: str) -> str:
    render_module = sys.modules.get("core.cli.python_cli.workflow.tui.monitor.core._render_mixin")
    display = getattr(render_module, "_get_role_display", _get_role_display) if render_module else _get_role_display
    return display(node)


class _RoleCardMixin:

    def _build_leader_state(self, active: str, buf: str, pt: int, ct: int) -> dict:
        sess_sub = getattr(self, "_leader_session_substate", "")
        sess_det = getattr(self, "_leader_session_detail", "")
        explicit_session_substate = sess_sub in ("reading", "thinking", "writing")
        if explicit_session_substate:
            substate = sess_sub
            detail   = sess_det
        else:
            substate = getattr(self, "_leader_substate", "idle")
            if substate == "generating":
                substate = "thinking"
            detail = ""

        reasoning_active = getattr(self, "_reasoning_active", False)
        reasoning_acc    = getattr(self, "_reasoning_acc", "")

        return {
            "substate":         substate,
            "detail":           detail,
            "read_elapsed":     getattr(self, "_leader_read_elapsed", 0) if substate != "reading" else 0,
            "read_pt":          pt,
            "reasoning_acc":    reasoning_acc,
            "reasoning_active": reasoning_active,
            "buf":     buf,
            "pt":      pt,
            "ct":      ct,
            "attempt": getattr(self, "_attempt_count", 1),
            "is_done": False,
        }

    def _render_active_role_cards(
        self, active: str, sc: str, buf: str, snap: dict
    ) -> str:
        """Render all role substates that are currently reporting activity."""
        from ..helpers import _parse_token_counts_for_node
        from ..state import (
            render_ambassador_running,
            render_explainer_tree,
        )
        from ..state._leader import render_leader_tree
        from ..state._tool_curator import render_curator_tree
        from ..state._worker import render_worker_tree
        from ..state._secretary import render_secretary_tree

        cards: list[str] = []

        amb_sub = getattr(self, "_ambassador_substate", "")
        amb_det = getattr(self, "_ambassador_detail", "")
        if amb_sub or amb_det:
            pt_a, ct_a = _parse_token_counts_for_node("ambassador")
            elapsed_a = int(time.time() - self._state_start_times.get("ambassador", time.time())) if hasattr(self, "_state_start_times") else 0
            cards.append(render_ambassador_running(
                sc,
                _display_role("ambassador"),
                buf if active == "ambassador" else "",
                pt_a, ct_a, self._attempt_count, elapsed_a,
                reasoning_acc=self._reasoning_acc if active == "ambassador" else "",
                reasoning_active=self._reasoning_active if active == "ambassador" else False,
                substate=amb_sub, detail=amb_det,
            ))

        leader_sub = getattr(self, "_leader_session_substate", "")
        leader_det = getattr(self, "_leader_session_detail", "")
        if leader_sub or leader_det:
            pt_l, ct_l = _parse_token_counts_for_node("leader_generate")
            elapsed_l = int(time.time() - getattr(self, "_leader_substate_start", time.time()))
            cards.append(render_leader_tree(
                sc,
                _display_role("leader_generate"),
                self._build_leader_state("leader_generate", buf if active == "leader_generate" else "", pt_l, ct_l),
                elapsed_l,
            ))

        curator_sub = getattr(self, "_curator_substate", "")
        curator_det = getattr(self, "_curator_detail", "")
        if curator_sub or curator_det:
            pt_c, ct_c = _parse_token_counts_for_node("tool_curator")
            elapsed_c = int(time.time() - (getattr(self, "_curator_started_at", 0.0) or time.time()))
            cards.append(render_curator_tree(sc, _display_role("tool_curator"), {
                "substate": curator_sub or "reading",
                "detail": curator_det,
                "pt": pt_c, "ct": ct_c,
                "buf": buf if active == "tool_curator" else "",
                "is_done": False,
            }, elapsed_c))

        workers_state = getattr(self, "_workers_state", {}) or {}
        for worker_key, worker_state in workers_state.items():
            worker_sub    = str(worker_state.get("substate") or "")
            worker_detail = str(worker_state.get("detail") or "")
            worker_files  = list(worker_state.get("reading_files") or [])
            worker_cmd    = str(worker_state.get("using_cmd") or "")
            if not (worker_sub or worker_detail or worker_files or worker_cmd):
                continue
            pt_w, ct_w = _parse_token_counts_for_node(worker_key)
            elapsed_w = int(time.time() - self._state_start_times.get(worker_key, time.time())) if hasattr(self, "_state_start_times") else 0
            cards.append(render_worker_tree(sc, worker_key, {
                "substate": worker_sub or "reading",
                "detail": worker_detail,
                "reading_files": worker_files,
                "using_cmd": worker_cmd,
                "pt": pt_w, "ct": ct_w,
                "buf": buf if active.lower() == worker_key.lower() else "",
                "is_done": False,
            }, elapsed_w))

        worker_sub    = "" if workers_state else getattr(self, "_worker_substate", "")
        worker_detail = getattr(self, "_worker_detail", "")
        worker_files  = getattr(self, "_worker_reading_files", [])
        worker_cmd    = getattr(self, "_worker_using_cmd", "")
        if worker_sub or worker_detail or worker_files or worker_cmd:
            pt_w, ct_w = _parse_token_counts_for_node("worker")
            elapsed_w = int(time.time() - self._state_start_times.get("worker", time.time())) if hasattr(self, "_state_start_times") else 0
            cards.append(render_worker_tree(sc, _display_role("worker"), {
                "substate": worker_sub or "reading",
                "detail": worker_detail,
                "reading_files": worker_files,
                "using_cmd": worker_cmd,
                "pt": pt_w, "ct": ct_w,
                "buf": buf if active in ("worker", "restore_worker") else "",
                "is_done": False,
            }, elapsed_w))

        secretary_sub      = getattr(self, "_secretary_substate", "")
        secretary_detail   = getattr(self, "_secretary_detail", "")
        secretary_commands = getattr(self, "_secretary_commands", [])
        if secretary_sub or secretary_detail or secretary_commands:
            elapsed_s = int(time.time() - self._state_start_times.get("secretary", time.time())) if hasattr(self, "_state_start_times") else 0
            cards.append(render_secretary_tree(sc, _display_role("secretary"), {
                "substate": secretary_sub or "asking",
                "detail": secretary_detail,
                "command_results": secretary_commands,
                "is_done": False,
            }, elapsed_s))

        explainer_sub    = getattr(self, "_explainer_substate", "")
        explainer_detail = getattr(self, "_explainer_detail", "")
        if explainer_sub or explainer_detail:
            mode = "file" if explainer_sub == "reading" else "codebase"
            cards.append(render_explainer_tree(sc, _display_role("explainer"), {
                "substate": explainer_sub or "using",
                "detail": explainer_detail,
                "mode": mode,
                "buf": "",
                "is_done": False,
            }, 0))

        return "\n\n".join(card for card in cards if card)
