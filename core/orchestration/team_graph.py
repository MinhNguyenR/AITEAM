"""
LangGraph team workflow aligned with the CLI start pipeline.

Ownership lives in orchestration; `agents.team_map._team_map` remains a
compatibility shim for older imports.
"""

from __future__ import annotations

from typing import Sequence

from core.bootstrap import ensure_project_root

ensure_project_root()

from langgraph.graph import END, START, StateGraph

from .team_nodes import (
    node_end_failed,
    node_finalize_phase1,
    node_human_context_gate,
    node_leader_generate,
    node_tool_curator,
)
from .team_routing import route_after_leader, route_entry
from .team_state import TeamState


_builder: StateGraph | None = None


def _build_graph() -> StateGraph:
    global _builder
    if _builder is not None:
        return _builder
    graph = StateGraph(TeamState)
    graph.add_node("leader_generate", node_leader_generate)
    graph.add_node("human_context_gate", node_human_context_gate)
    graph.add_node("tool_curator", node_tool_curator)
    graph.add_node("finalize_phase1", node_finalize_phase1)
    graph.add_node("end_failed", node_end_failed)

    graph.add_conditional_edges(
        START,
        route_entry,
        {"leader_generate": "leader_generate", "human_context_gate": "human_context_gate"},
    )
    graph.add_conditional_edges(
        "leader_generate",
        route_after_leader,
        {"human_context_gate": "human_context_gate", "end_failed": "end_failed"},
    )
    graph.add_edge("human_context_gate", "tool_curator")
    graph.add_edge("tool_curator", "finalize_phase1")
    graph.add_edge("finalize_phase1", END)
    graph.add_edge("end_failed", END)
    _builder = graph
    return graph


def get_graph(checkpointer=None, interrupt_before: Sequence[str] | None = None):
    seq = interrupt_before if interrupt_before is not None else ("human_context_gate",)
    return _build_graph().compile(checkpointer=checkpointer, interrupt_before=list(seq))


__all__ = ["TeamState", "get_graph", "route_entry", "route_after_leader"]
