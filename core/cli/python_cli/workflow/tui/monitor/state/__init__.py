"""Workflow live-display state renderers.

Each sub-module handles one workflow actor / lifecycle phase.
All functions return Rich markup strings — no side effects.
"""
from __future__ import annotations

from ._ambassador import render_running as render_ambassador_running
from ._ambassador import render_done    as render_ambassador_done
from ._leader     import render_regen_starting as render_leader_regen_starting
from ._tool_curator import render_curator_tree, render_curator_done
from ._gate       import render_waiting     as render_gate_waiting
from ._gate       import render_checking    as render_gate_checking
from ._gate       import render_editing     as render_gate_editing
from ._gate       import render_accepted    as render_gate_accepted
from ._gate       import render_declined    as render_gate_declined
from ._clarify    import render_pending     as render_clarify_pending
from ._pipeline   import (
    render_idle,
    render_transitional,
    render_finalizing,
    render_btw_injecting,
    render_unknown,
)

__all__ = [
    "render_ambassador_running", "render_ambassador_done",
    "render_leader_regen_starting",
    "render_curator_tree", "render_curator_done",
    "render_gate_waiting", "render_gate_checking", "render_gate_editing",
    "render_gate_accepted", "render_gate_declined",
    "render_clarify_pending",
    "render_idle", "render_transitional", "render_finalizing",
    "render_btw_injecting", "render_unknown",
]
