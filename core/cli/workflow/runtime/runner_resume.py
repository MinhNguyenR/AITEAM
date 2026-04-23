"""Resume workflow after a human gate pause."""

from __future__ import annotations

import logging

from agents.team_map._team_map import get_graph
from .checkpointer import get_checkpointer
from . import session as ws

logger = logging.getLogger(__name__)


def resume_workflow() -> bool:
    tid = ws.get_thread_id()
    if not tid or not ws.is_paused_for_review():
        return False
    ws.set_phase_running()
    ws.set_pipeline_paused_at_gate(False)
    ws.set_pipeline_active_step("human_context_gate")

    ib = ws.get_interrupt_before()
    graph = get_graph(get_checkpointer(), interrupt_before=ib)
    config = {"configurable": {"thread_id": tid}}
    try:
        while True:
            graph.invoke(None, config)
            snap = graph.get_state(config)
            if not snap.next:
                break
    except (RuntimeError, ValueError, OSError, KeyError, TypeError):
        logger.exception("workflow resume failed")
        return False

    ws.set_paused_for_review(False)
    ws.set_last_node(None)
    ws.set_pipeline_run_finished(True)
    ws.set_pipeline_active_step("idle")
    ws.set_pipeline_stop_phase("idle")
    if ws.get_context_accept_status() not in {"accepted", "deferred"}:
        ws.set_context_accept_status("none")
    return True
