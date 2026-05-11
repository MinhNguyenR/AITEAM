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
    node_parallel_join,
    node_parallel_prepare,
    node_secretary,
    node_secretary_setup,
    node_tool_curator,
    node_worker_a,
    node_worker_b,
    node_worker_c,
    node_worker_d,
    node_worker_e,
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
    graph.add_node("parallel_prepare", node_parallel_prepare)
    graph.add_node("secretary_setup", node_secretary_setup)
    graph.add_node("worker_a", node_worker_a)
    graph.add_node("worker_b", node_worker_b)
    graph.add_node("worker_c", node_worker_c)
    graph.add_node("worker_d", node_worker_d)
    graph.add_node("worker_e", node_worker_e)
    graph.add_node("parallel_join", node_parallel_join)
    graph.add_node("secretary", node_secretary)
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
    graph.add_edge("human_context_gate", "parallel_prepare")
    graph.add_edge("human_context_gate", "tool_curator")
    graph.add_edge(["parallel_prepare", "tool_curator"], "secretary_setup")
    graph.add_edge("secretary_setup", "worker_a")
    graph.add_edge("secretary_setup", "worker_b")
    graph.add_edge("secretary_setup", "worker_c")
    graph.add_edge("secretary_setup", "worker_d")
    graph.add_edge("secretary_setup", "worker_e")
    graph.add_edge(["worker_a", "worker_b", "worker_c", "worker_d", "worker_e"], "parallel_join")
    graph.add_edge("parallel_join", "secretary")
    graph.add_edge("secretary", "finalize_phase1")
    graph.add_edge("finalize_phase1", END)
    graph.add_edge("end_failed", END)
    _builder = graph
    return graph


def get_graph(checkpointer=None, interrupt_before: Sequence[str] | None = None):
    seq = interrupt_before if interrupt_before is not None else ("human_context_gate",)
    return _build_graph().compile(checkpointer=checkpointer, interrupt_before=list(seq))


__all__ = ["TeamState", "get_graph", "route_entry", "route_after_leader"]
