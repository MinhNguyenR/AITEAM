"""Tests for core/domain/prompts.py — prompt builder functions."""
from core.domain.prompts import (
    AMBASSADOR_SYSTEM_PROMPT,
    ASK_MODE_SYSTEM_PROMPT,
    build_expert_coplan_prompt,
    build_expert_solo_prompt,
    build_leader_high_prompt,
    build_leader_low_prompt,
    build_leader_medium_prompt,
)


class TestAmbassadorSystemPrompt:
    def test_contains_tier_definitions(self):
        assert "LOW" in AMBASSADOR_SYSTEM_PROMPT
        assert "MEDIUM" in AMBASSADOR_SYSTEM_PROMPT
        assert "EXPERT" in AMBASSADOR_SYSTEM_PROMPT
        assert "HARD" in AMBASSADOR_SYSTEM_PROMPT

    def test_is_string(self):
        assert isinstance(AMBASSADOR_SYSTEM_PROMPT, str)
        assert len(AMBASSADOR_SYSTEM_PROMPT) > 100


class TestBuildLeaderMediumPrompt:
    def test_includes_state(self):
        result = build_leader_medium_prompt('{"task": "test"}')
        assert '{"task": "test"}' in result

    def test_contains_required_sections(self):
        result = build_leader_medium_prompt("state")
        assert "DIRECTORY STRUCTURE" in result
        assert "FILE MAP" in result
        assert "DATA FLOW" in result
        assert "ATOMIC TASKS" in result

    def test_returns_string(self):
        assert isinstance(build_leader_medium_prompt(""), str)


class TestBuildLeaderLowPrompt:
    def test_includes_state(self):
        result = build_leader_low_prompt("my state data")
        assert "my state data" in result

    def test_contains_sections(self):
        result = build_leader_low_prompt("")
        assert "DIRECTORY STRUCTURE" in result
        assert "ATOMIC TASKS" in result

    def test_mentions_low_complexity(self):
        result = build_leader_low_prompt("")
        assert "LOW" in result


class TestBuildLeaderHighPrompt:
    def test_includes_state(self):
        result = build_leader_high_prompt("hard state")
        assert "hard state" in result

    def test_contains_risk_register(self):
        result = build_leader_high_prompt("")
        assert "RISK REGISTER" in result

    def test_mentions_hard(self):
        result = build_leader_high_prompt("")
        assert "HARD" in result


class TestBuildExpertSoloPrompt:
    def test_includes_state_as_json(self):
        state = {"task": "build something", "tier": "EXPERT"}
        result = build_expert_solo_prompt(state)
        assert '"task"' in result
        assert "build something" in result

    def test_contains_required_structure(self):
        result = build_expert_solo_prompt({})
        assert "DIRECTORY" in result
        assert "Atomic Tasks" in result or "ATOMIC TASKS" in result or "atomic" in result.lower()


class TestBuildExpertCoplanPrompt:
    def test_includes_draft(self):
        result = build_expert_coplan_prompt("# My Plan\n## Sections", {"task": "x"})
        assert "# My Plan" in result

    def test_includes_state(self):
        result = build_expert_coplan_prompt("draft", {"tier": "EXPERT"})
        assert "EXPERT" in result

    def test_no_state(self):
        result = build_expert_coplan_prompt("draft", {})
        assert isinstance(result, str)
        assert "draft" in result


class TestAskModeSystemPrompt:
    def test_is_nonempty_string(self):
        assert isinstance(ASK_MODE_SYSTEM_PROMPT, str)
        assert len(ASK_MODE_SYSTEM_PROMPT) > 10
