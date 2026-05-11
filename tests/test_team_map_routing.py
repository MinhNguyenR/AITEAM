"""Tests for agents/team_map/_team_map.py — pure routing functions."""
import sys
from unittest.mock import MagicMock, patch

import pytest

_MOCKS = {
    "langgraph.graph": MagicMock(END="__end__", START="__start__", StateGraph=MagicMock()),
    "core.cli.python_cli.workflow.runtime.session": MagicMock(),
    "utils.logger": MagicMock(artifact_detail=lambda *a, **kw: "", workflow_event=MagicMock()),
}


@pytest.fixture(autouse=True)
def _stub_heavy_imports(monkeypatch):
    """Isolate the routing module from heavy dependencies for every test."""
    # Remove any previously cached version so we always get a fresh import
    monkeypatch.delitem(sys.modules, "agents.team_map._team_map", raising=False)
    with patch.dict(sys.modules, _MOCKS):
        yield


@pytest.fixture
def routing():
    from agents.team_map._team_map import route_entry, route_after_leader
    return route_entry, route_after_leader


class TestRouteEntry:
    def _state(self, tier):
        return {"brief_dict": {"tier": tier}}

    def test_low_tier_goes_to_leader(self, routing):
        route_entry, _ = routing
        assert route_entry(self._state("LOW")) == "leader_generate"

    def test_expert_tier_falls_back_to_leader(self, routing):
        route_entry, _ = routing
        assert route_entry(self._state("EXPERT")) == "leader_generate"

    def test_medium_tier_goes_to_leader(self, routing):
        route_entry, _ = routing
        assert route_entry(self._state("MEDIUM")) == "leader_generate"

    def test_hard_tier_goes_to_leader(self, routing):
        route_entry, _ = routing
        assert route_entry(self._state("HARD")) == "leader_generate"

    def test_default_missing_tier_goes_to_leader(self, routing):
        route_entry, _ = routing
        assert route_entry({"brief_dict": {}}) == "leader_generate"


class TestRouteAfterLeader:
    def _state(self, tier="MEDIUM", failed=False, ctx="/path/context.md"):
        return {
            "brief_dict": {"tier": tier},
            "leader_failed": failed,
            "context_path": ctx,
        }

    def test_failed_leader_ends(self, routing):
        _, route_after_leader = routing
        assert route_after_leader(self._state(failed=True)) == "end_failed"

    def test_no_context_path_ends(self, routing):
        _, route_after_leader = routing
        assert route_after_leader(self._state(ctx=None)) == "end_failed"

    def test_hard_tier_goes_to_gate(self, routing):
        _, route_after_leader = routing
        assert route_after_leader(self._state(tier="HARD")) == "human_context_gate"

    def test_medium_tier_goes_to_gate(self, routing):
        _, route_after_leader = routing
        assert route_after_leader(self._state(tier="MEDIUM")) == "human_context_gate"

    def test_low_tier_goes_to_gate(self, routing):
        _, route_after_leader = routing
        assert route_after_leader(self._state(tier="LOW")) == "human_context_gate"
