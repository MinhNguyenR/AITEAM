from __future__ import annotations

from .team_state import TeamState


def route_entry(state: TeamState) -> str:
    _ = state
    return "leader_generate"


def route_after_leader(state: TeamState) -> str:
    if state.get("leader_failed") or not state.get("context_path"):
        return "end_failed"
    return "human_context_gate"


__all__ = ["route_entry", "route_after_leader"]

