"""Tests for core/domain/prompts.py — prompt builder functions."""
from core.domain.prompts import (
    AMBASSADOR_SYSTEM_PROMPT,
    ASK_MODE_SYSTEM_PROMPT,
    LEADER_SYSTEM_PROMPT,
    EXPERT_SYSTEM_PROMPT,
    EXPERT_COPLAN_SYSTEM_PROMPT,
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
        assert "HARD" in AMBASSADOR_SYSTEM_PROMPT
        assert "Never output EXPERT or ARCHITECT" in AMBASSADOR_SYSTEM_PROMPT

    def test_is_string(self):
        assert isinstance(AMBASSADOR_SYSTEM_PROMPT, str)
        assert len(AMBASSADOR_SYSTEM_PROMPT) > 100


class TestBuildLeaderMediumPrompt:
    def test_includes_state(self):
        result = build_leader_medium_prompt('{"task": "test"}')
        assert '{"task": "test"}' in result

    def test_contains_required_sections(self):
        result = build_leader_medium_prompt("state")
        assert "Tier: MEDIUM" in result
        assert "Steps: 5-8" in result
        assert "ask up to 2 high-value clarification questions" in result

    def test_returns_string(self):
        assert isinstance(build_leader_medium_prompt(""), str)


class TestBuildLeaderLowPrompt:
    def test_includes_state(self):
        result = build_leader_low_prompt("my state data")
        assert "my state data" in result

    def test_contains_sections(self):
        result = build_leader_low_prompt("")
        assert "Tier: LOW" in result
        assert "Steps: 3-6" in result

    def test_mentions_low_complexity(self):
        result = build_leader_low_prompt("")
        assert "LOW" in result


class TestBuildLeaderHighPrompt:
    def test_includes_state(self):
        result = build_leader_high_prompt("hard state")
        assert "hard state" in result

    def test_contains_risk_register(self):
        result = build_leader_high_prompt("")
        assert "Tier: HARD" in result
        assert "HARDWARE line" in result

    def test_mentions_hard(self):
        result = build_leader_high_prompt("")
        assert "HARD" in result


class TestBuildExpertSoloPrompt:
    def test_includes_state_as_json(self):
        state = {"task": "build something", "tier": "HARD"}
        result = build_expert_solo_prompt(state)
        assert '"task"' in result
        assert "build something" in result

    def test_contains_required_structure(self):
        result = build_expert_solo_prompt({})
        assert "architecture validator/co-planner" in result
        assert "at least 8 atomic implementation tasks" in result


class TestBuildExpertCoplanPrompt:
    def test_includes_draft(self):
        result = build_expert_coplan_prompt("# My Plan\n## Sections", {"task": "x"})
        assert "# My Plan" in result

    def test_includes_state(self):
        result = build_expert_coplan_prompt("draft", {"tier": "HARD"})
        assert "HARD" in result

    def test_no_state(self):
        result = build_expert_coplan_prompt("draft", {})
        assert isinstance(result, str)
        assert "draft" in result


class TestAskModeSystemPrompt:
    def test_is_nonempty_string(self):
        assert isinstance(ASK_MODE_SYSTEM_PROMPT, str)
        assert len(ASK_MODE_SYSTEM_PROMPT) > 10

    def test_settings_commands_match_runtime(self):
        assert "`1` toggle auto-accept" in ASK_MODE_SYSTEM_PROMPT
        assert "`2` cycle context action (`ask/accept/decline`)" in ASK_MODE_SYSTEM_PROMPT
        assert "`3` toggle help external terminal" in ASK_MODE_SYSTEM_PROMPT


class TestPlannerPromptContracts:
    def test_leader_system_requires_clarification(self):
        assert "ask at most 2 high-value clarification questions first" in LEADER_SYSTEM_PROMPT

    def test_expert_prompts_are_nonlegacy(self):
        assert "EXPERT-tier" not in EXPERT_SYSTEM_PROMPT
        assert "EXPERT-tier" not in EXPERT_COPLAN_SYSTEM_PROMPT
