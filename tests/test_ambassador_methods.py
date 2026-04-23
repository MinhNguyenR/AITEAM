"""Tests for agents/ambassador.py — execute, format_output, parse, _build helpers."""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


def _make_ambassador():
    from agents.ambassador import Ambassador
    cfg = {
        "model": "gpt-4o-mini",
        "max_tokens": 300,
        "temperature": 0.1,
        "role": "Ambassador",
    }
    with patch("agents.base_agent.OpenAI"), \
         patch("agents.ambassador.config") as mc:
        mc.get_worker.return_value = cfg
        mc.get_model_for_tier.return_value = "gpt-4o"
        amb = Ambassador()
    return amb, mc


class TestAmbassadorInit:
    def test_init_sets_last_usage_event(self):
        amb, _ = _make_ambassador()
        assert isinstance(amb.last_usage_event, dict)


class TestBuildDeltaBrief:
    def test_cuda_tier_upgraded_to_hard(self):
        amb, _ = _make_ambassador()
        llm = {"tier": "MEDIUM", "is_cuda_required": True, "complexity_score": 0.5}
        with patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="LEADER_HIGH"):
            mc.get_model_for_tier.return_value = "gemini-pro"
            brief = amb._build_delta_brief("cuda kernel", llm, None, "cuda")
        assert brief.tier == "HARD"

    def test_high_complexity_becomes_expert(self):
        amb, _ = _make_ambassador()
        llm = {"tier": "MEDIUM", "is_cuda_required": False, "complexity_score": 0.9,
               "is_hardware_bound": False}
        with patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="EXPERT_MIMO"):
            mc.get_model_for_tier.return_value = "gpt-4"
            brief = amb._build_delta_brief("complex algo", llm, None, "python")
        assert brief.tier == "EXPERT"

    def test_normal_medium_stays(self):
        amb, _ = _make_ambassador()
        llm = {"tier": "MEDIUM", "is_cuda_required": False, "complexity_score": 0.5,
               "is_hardware_bound": False, "summary": "Build API"}
        with patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="LEADER_MEDIUM"):
            mc.get_model_for_tier.return_value = "kimi-k2"
            brief = amb._build_delta_brief("build api", llm, None, "python")
        assert brief.tier == "MEDIUM"


class TestBuildFallbackDeltaBrief:
    def test_cuda_pattern_sets_cuda_flag(self):
        amb, _ = _make_ambassador()
        with patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="LEADER_HIGH"):
            mc.get_model_for_tier.return_value = "gemini"
            brief = amb._build_fallback_delta_brief("write cuda kernel", None, "cuda")
        assert brief.is_cuda_required is True

    def test_hardware_pattern_sets_hw_flag(self):
        amb, _ = _make_ambassador()
        with patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="LEADER_HIGH"):
            mc.get_model_for_tier.return_value = "gpt-4"
            brief = amb._build_fallback_delta_brief("optimize VRAM usage", None, "python")
        assert brief.is_hardware_bound is True

    def test_low_tier_prompt_fallback(self):
        amb, _ = _make_ambassador()
        with patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="LEADER_LOW"):
            mc.get_model_for_tier.return_value = "deepseek"
            brief = amb._build_fallback_delta_brief("giải thích python decorator", None, "python")
        assert brief.tier in ("LOW", "MEDIUM", "HARD", "EXPERT")


class TestParse:
    def test_parse_uses_fallback_on_api_error(self):
        amb, _ = _make_ambassador()
        with patch.object(amb, "_call_parse_api", side_effect=RuntimeError("API down")), \
             patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="LEADER_MEDIUM"):
            mc.get_model_for_tier.return_value = "test-model"
            brief = amb.parse("explain python generators")
        assert brief.tier in ("LOW", "MEDIUM", "EXPERT", "HARD")

    def test_parse_calls_api_on_success(self):
        amb, _ = _make_ambassador()
        llm_response = {"tier": "MEDIUM", "summary": "Build API", "complexity_score": 0.5}
        with patch.object(amb, "_call_parse_api", return_value=llm_response), \
             patch("agents.ambassador.config") as mc, \
             patch("agents.ambassador.selected_leader_for_tier", return_value="LEADER_MEDIUM"):
            mc.get_model_for_tier.return_value = "kimi-k2"
            brief = amb.parse("build a REST API")
        assert brief.tier == "MEDIUM"


class TestExecute:
    def test_execute_returns_json(self):
        amb, mock_cfg = _make_ambassador()
        mock_cfg.get_model_for_tier.return_value = "test"
        with patch.object(amb, "parse") as mock_parse, \
             patch.object(amb, "log_action"):
            mock_brief = MagicMock()
            mock_brief.tier = "MEDIUM"
            mock_brief.selected_leader = "LEADER_MEDIUM"
            mock_brief.task_uuid = "uuid-123"
            mock_brief.summary = "Build CRUD"
            mock_brief.language_detected = "python"
            mock_brief.is_cuda_required = False
            mock_brief.estimated_vram_usage = None
            mock_brief.is_hardware_bound = False
            mock_parse.return_value = mock_brief
            result = amb.execute("build a CRUD app")

        output = json.loads(result)
        assert output["difficulty"] == "MEDIUM"
        assert "task_id" in output
        assert output["next_step"] == "CREATE_CONTEXT_MD"

    def test_execute_cuda_adds_constraint(self):
        amb, mock_cfg = _make_ambassador()
        mock_cfg.get_model_for_tier.return_value = "test"
        with patch.object(amb, "parse") as mock_parse, \
             patch.object(amb, "log_action"):
            mock_brief = MagicMock()
            mock_brief.tier = "HARD"
            mock_brief.selected_leader = "LEADER_HIGH"
            mock_brief.task_uuid = "uuid-456"
            mock_brief.summary = "CUDA kernel"
            mock_brief.language_detected = "cuda"
            mock_brief.is_cuda_required = True
            mock_brief.estimated_vram_usage = "8GB"
            mock_brief.is_hardware_bound = True
            mock_parse.return_value = mock_brief
            result = amb.execute("cuda kernel")

        output = json.loads(result)
        assert "CUDA required" in output["brief"]["constraints"]
        assert output["brief"]["scope"] == ["*.cu"]

    def test_execute_expert_sets_escalated(self):
        amb, mock_cfg = _make_ambassador()
        with patch.object(amb, "parse") as mock_parse, \
             patch.object(amb, "log_action"):
            mock_brief = MagicMock()
            mock_brief.tier = "EXPERT"
            mock_brief.selected_leader = "EXPERT"
            mock_brief.task_uuid = "uuid-789"
            mock_brief.summary = "Complex algo"
            mock_brief.language_detected = "python"
            mock_brief.is_cuda_required = False
            mock_brief.estimated_vram_usage = None
            mock_brief.is_hardware_bound = False
            mock_parse.return_value = mock_brief
            result = amb.execute("complex optimization")

        output = json.loads(result)
        assert output["is_escalated"] is True


class TestFormatOutput:
    def test_parses_and_reformats_valid_json(self):
        amb, _ = _make_ambassador()
        raw = '{"key": "value"}'
        result = amb.format_output(raw)
        parsed = json.loads(result)
        assert parsed["key"] == "value"

    def test_invalid_json_returned_as_is(self):
        amb, _ = _make_ambassador()
        raw = "not valid json at all"
        result = amb.format_output(raw)
        assert result == raw

    def test_strips_fences_from_json(self):
        amb, _ = _make_ambassador()
        raw = '```json\n{"tier": "MEDIUM"}\n```'
        result = amb.format_output(raw)
        parsed = json.loads(result)
        assert parsed["tier"] == "MEDIUM"


class TestGetTierInfo:
    def test_returns_tier_info(self):
        from agents.ambassador import Ambassador
        with patch("agents.ambassador.config") as mc:
            mc.get_model_for_tier.return_value = "kimi-k2"
            info = Ambassador.get_tier_info("medium")
        assert info["tier"] == "MEDIUM"
        assert "description" in info
