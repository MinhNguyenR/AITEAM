"""Tests for agents/team_map/_team_map.py — pure routing functions."""
import sys
from unittest.mock import MagicMock, patch

import pytest

# test_runner_rewind_pure.py runs first alphabetically and stubs agents.team_map._team_map.
# Remove that stub so we can import the real module here.
sys.modules.pop("agents.team_map._team_map", None)

# Stub out heavy imports so we can import the module in isolation
_MOCKS = {
    "langgraph.graph": MagicMock(END="__end__", START="__start__", StateGraph=MagicMock()),
    "core.cli.workflow.runtime.session": MagicMock(),
    "utils.logger": MagicMock(artifact_detail=lambda *a, **kw: "", workflow_event=MagicMock()),
}
for mod, mock in _MOCKS.items():
    sys.modules.setdefault(mod, mock)

# Now import the pure routing functions
from agents.team_map._team_map import route_entry, route_after_leader, route_after_expert_solo


class TestRouteEntry:
    def _state(self, tier):
        return {"brief_dict": {"tier": tier}}

    def test_low_tier_goes_to_leader(self):
        assert route_entry(self._state("LOW")) == "leader_generate"

    def test_expert_tier_goes_to_expert_solo(self):
        assert route_entry(self._state("EXPERT")) == "expert_solo"

    def test_medium_tier_goes_to_leader(self):
        assert route_entry(self._state("MEDIUM")) == "leader_generate"

    def test_hard_tier_goes_to_leader(self):
        assert route_entry(self._state("HARD")) == "leader_generate"

    def test_default_missing_tier_goes_to_leader(self):
        assert route_entry({"brief_dict": {}}) == "leader_generate"


class TestRouteAfterLeader:
    def _state(self, tier="MEDIUM", failed=False, ctx="/path/context.md"):
        return {
            "brief_dict": {"tier": tier},
            "leader_failed": failed,
            "context_path": ctx,
        }

    def test_failed_leader_ends(self):
        assert route_after_leader(self._state(failed=True)) == "end_failed"

    def test_no_context_path_ends(self):
        assert route_after_leader(self._state(ctx=None)) == "end_failed"

    def test_hard_tier_goes_to_coplan(self):
        assert route_after_leader(self._state(tier="HARD")) == "expert_coplan"

    def test_medium_tier_goes_to_gate(self):
        assert route_after_leader(self._state(tier="MEDIUM")) == "human_context_gate"

    def test_low_tier_goes_to_gate(self):
        assert route_after_leader(self._state(tier="LOW")) == "human_context_gate"


class TestRouteAfterExpertSolo:
    def test_no_context_path_ends(self):
        assert route_after_expert_solo({"context_path": None}) == "end_failed"

    def test_empty_context_path_ends(self):
        assert route_after_expert_solo({"context_path": ""}) == "end_failed"

    def test_valid_context_goes_to_gate(self):
        assert route_after_expert_solo({"context_path": "/path/context.md"}) == "human_context_gate"
