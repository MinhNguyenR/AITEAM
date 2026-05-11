"""Mixin: _on_step_transition -- step lifecycle events and substate resets."""
from __future__ import annotations

import time

from core.cli.python_cli.i18n import t
from ._constants import _GEN_STEPS, _ACTION, _ACTION_DONE, _GATE_ACCEPTED
from ._utils import _get_role_display


def _get_done_markup(node: str, role: str, tok: str, st: dict = None) -> str:
    from ..state import render_ambassador_done, render_curator_done, render_worker_done, render_secretary_done
    from ..state._leader import render_leader_tree
    if node == "ambassador":
        return render_ambassador_done(role, tok)
    elif node == "leader_generate" and st:
        st['is_done'] = True
        return render_leader_tree("[bold green]✔[/bold green]", role, st, tok=tok)
    elif node == "tool_curator":
        return render_curator_done(role, tok)
    elif node in ("worker", "restore_worker"):
        files = st.get("files_written", 0) if st else 0
        return render_worker_done(role, files_written=files, tok=tok)
    elif node == "secretary":
        passed = st.get("passed", 0) if st else 0
        total = st.get("total", 0) if st else 0
        return render_secretary_done(role, passed=passed, total=total)
    return ""


class _TransitionMixin:

    def _on_step_transition(self, prev: str, active: str) -> None:
        from ....runtime import session as ws
        from ..helpers import _parse_token_counts_for_node

        pt, ct = _parse_token_counts_for_node(prev) if prev in _GEN_STEPS else (0, 0)

        if prev in _GEN_STEPS:
            role        = _get_role_display(prev)
            done_action = _ACTION_DONE.get(prev, _ACTION.get(prev, prev))
            tok         = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""

            _skip_header = (prev == "ambassador" and self._ambassador_done_written)
            if prev == "ambassador":
                self._ambassador_done_written = True
            self._completed_nodes.add(prev)

            if not _skip_header:
                self._write("")
                st = None
                if prev == "leader_generate":
                    st = self._build_leader_state(prev, "", pt, ct)
                elif prev == "worker":
                    files = len(getattr(self, "_worker_reading_files", []))
                    st = {"files_written": files}
                elif prev == "secretary":
                    cmds = getattr(self, "_secretary_commands", [])
                    st = {
                        "passed": sum(1 for c in cmds if c.get("success")),
                        "total":  len(cmds),
                    }
                done_markup = _get_done_markup(prev, role, tok, st)
                if done_markup:
                    self._write(done_markup)
                else:
                    self._write(f"[bold green]✔[/bold green] [bold]{role}[/bold]  {done_action}{tok}")

            if prev == "leader_generate":
                self._leader_substate = "idle"
                try:
                    ws.clear_leader_substate()
                except Exception:
                    pass
            if prev == "ambassador":
                try:
                    ws.clear_ambassador_substate()
                except Exception:
                    pass
            if prev in ("worker", "restore_worker"):
                try:
                    ws.clear_worker_state(getattr(self, "_worker_key", "WORKER_A"))
                except Exception:
                    pass
            if prev == "secretary":
                try:
                    ws.clear_secretary_substate()
                    ws.clear_secretary_commands()
                except Exception:
                    pass

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

        if active in ("worker", "restore_worker") and prev not in ("worker", "restore_worker"):
            self._worker_substate      = "reading"
            self._worker_reading_files = []
            self._worker_using_cmd     = ""

        if prev in ("worker", "restore_worker") and active not in ("worker", "restore_worker"):
            self._completed_nodes.add(prev)

        if active == "secretary" and prev != "secretary":
            self._secretary_substate = "asking"
            self._secretary_commands = []

        if prev == "secretary" and active != "secretary":
            self._completed_nodes.add("secretary")

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
            self._write(
                f"[bold green]✔[/bold green] [bold]context.md[/bold]  "
                f"[dim]{t('pipeline.gen_context').lower()} -- {time.strftime('%H:%M:%S')}[/dim]  "
                f"[dim][bold]/check[/bold] {t('nav.choose').lower()} . [bold]/accept[/bold] . [bold]/delete[/bold][/dim]"
            )
            self._scroll_offset = 0
