from __future__ import annotations


def test_team_graph_reexports_split_modules():
    from core.orchestration.team_graph import TeamState, route_after_leader, route_entry
    from core.orchestration.team_routing import route_after_leader as split_route_after_leader
    from core.orchestration.team_routing import route_entry as split_route_entry
    from core.orchestration.team_state import TeamState as split_team_state

    assert route_entry is split_route_entry
    assert route_after_leader is split_route_after_leader
    assert TeamState is split_team_state
