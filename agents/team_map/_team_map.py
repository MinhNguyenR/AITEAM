"""Backward-compatible shim for the workflow team graph."""

from core.orchestration.team_graph import TeamState, get_graph, route_after_leader, route_entry

__all__ = ["TeamState", "get_graph", "route_entry", "route_after_leader"]
