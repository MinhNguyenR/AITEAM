"""Tests for agents/leader.py — generate_context, execute, format_output, concrete leaders."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def _make_cfg(tmp_path, role_key="LEADER_MEDIUM"):
    cfg = {
        "model": "test-model",
        "max_tokens": 512,
        "temperature": 0.5,
        "role": role_key,
    }
    return cfg


def _make_base_leader(tmp_path):
    from agents.leader import BaseLeader

    class _ConcreteLeader(BaseLeader):
        def format_output(self, r):
            return r

    with patch("agents.base_agent.OpenAI"), \
         patch("agents.leader.config") as mc:
        mc.get_worker.return_value = _make_cfg(tmp_path)
        leader = _ConcreteLeader(
            agent_name="TestLeader",
            model_name="test-model",
            max_tokens=512,
            temperature=0.5,
            registry_role_key="LEADER_MEDIUM",
        )
    leader.data_dir = tmp_path
    return leader


def _write_state(tmp_path, data=None):
    state_dir = tmp_path / "task_abc"
    state_dir.mkdir(exist_ok=True)
    state_path = state_dir / "state.json"
    state_path.write_text(json.dumps(data or {"task": "test task", "tier": "MEDIUM"}), encoding="utf-8")
    return state_path


class TestGenerateContextSuccess:
    def test_writes_context_md(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        state_path = _write_state(tmp_path)

        with patch.object(leader, "call_api", return_value="## 1. DIRECTORY\nContent"), \
             patch("agents.leader.atomic_write_text") as mock_write, \
             patch.object(leader, "save_knowledge"), \
             patch.object(leader, "log_action"), \
             patch("utils.graphrag_utils.try_ingest_context"):
            result = leader.generate_context(str(state_path))

        assert mock_write.called
        assert result.endswith("context.md")

    def test_returns_no_context_on_empty_format_output(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        state_path = _write_state(tmp_path)
        leader.format_output = MagicMock(return_value="   ")

        with patch.object(leader, "call_api", return_value="some response"), \
             patch("agents.leader.atomic_write_text"), \
             patch.object(leader, "log_action"):
            result = leader.generate_context(str(state_path))

        assert "context.md" in result

    def test_raises_file_not_found_when_state_missing(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        with pytest.raises(FileNotFoundError):
            leader.generate_context(str(tmp_path / "missing_dir" / "state.json"))

    def test_call_api_value_error_writes_no_context(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        state_path = _write_state(tmp_path)

        with patch.object(leader, "call_api", side_effect=ValueError("finish_reason=length")), \
             patch("agents.leader.atomic_write_text"), \
             patch.object(leader, "log_action"):
            result = leader.generate_context(str(state_path))

        assert "context.md" in result

    def test_stream_mode_uses_call_api_stream(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        state_path = _write_state(tmp_path)

        with patch.object(leader, "call_api_stream", return_value="## 1. DIRECTORY\nContent") as mock_stream, \
             patch("agents.leader.atomic_write_text"), \
             patch.object(leader, "save_knowledge"), \
             patch.object(leader, "log_action"), \
             patch("utils.graphrag_utils.try_ingest_context"):
            leader.generate_context(str(state_path), stream_to_monitor=True)

        mock_stream.assert_called_once()


class TestExecuteMethod:
    def test_execute_delegates_to_generate_context(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        state_path = _write_state(tmp_path)

        with patch.object(leader, "generate_context", return_value=str(state_path.parent / "context.md")) as mock_gen:
            result = leader.execute("ignored_task", state_path=str(state_path))

        mock_gen.assert_called_once_with(str(state_path))

    def test_execute_uses_task_when_no_state_path(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        state_path = _write_state(tmp_path)

        with patch.object(leader, "generate_context", return_value="ctx.md") as mock_gen:
            leader.execute(str(state_path))

        mock_gen.assert_called_once_with(str(state_path))


class TestBuildPrompt:
    def test_build_prompt_returns_string(self, tmp_path):
        leader = _make_base_leader(tmp_path)
        result = leader._build_prompt({"task": "do something", "tier": "MEDIUM"})
        assert isinstance(result, str)
        assert len(result) > 0


def _make_leader_med(tmp_path):
    from agents.leader import LeaderMed
    with patch("agents.base_agent.OpenAI"), \
         patch("agents.leader.config") as mc:
        mc.get_worker.return_value = _make_cfg(tmp_path)
        leader = LeaderMed()
    leader.data_dir = tmp_path
    return leader


class TestFormatOutputEdgeCases:
    def test_regex_marker_fallback(self, tmp_path):
        leader = _make_leader_med(tmp_path)
        text = "Some preamble\n## 1. DIRECTORY\nActual content"
        result = leader.format_output(text)
        assert "## 1. DIRECTORY" in result
        assert "Some preamble" not in result

    def test_regex_fallback_when_no_standard_marker(self, tmp_path):
        leader = _make_leader_med(tmp_path)
        text = "Introduction text\n# 1. Overview\nContent here"
        result = leader.format_output(text)
        assert "Overview" in result

    def test_no_marker_returns_stripped(self, tmp_path):
        leader = _make_leader_med(tmp_path)
        text = "No section headers at all"
        result = leader.format_output(text)
        assert result == "No section headers at all"

class TestIsNoContext:
    def test_is_no_context_static(self, tmp_path):
        from agents.leader import BaseLeader
        ctx_path = tmp_path / "context.md"
        ctx_path.write_text("# NO_CONTEXT\nReason: timeout")
        assert BaseLeader.is_no_context(ctx_path) is True

    def test_is_no_context_false_for_valid(self, tmp_path):
        from agents.leader import BaseLeader
        ctx_path = tmp_path / "context.md"
        ctx_path.write_text("## 1. DIRECTORY\nSome content")
        assert BaseLeader.is_no_context(ctx_path) is False


class TestConcreteLeadersInit:
    def test_leader_low_init(self, tmp_path):
        from agents.leader import LeaderLow
        cfg = {"model": "deepseek-v3", "max_tokens": 8192, "temperature": 0.3}
        with patch("agents.base_agent.OpenAI"), \
             patch("agents.leader.config") as mc:
            mc.get_worker.return_value = cfg
            leader = LeaderLow()
        assert leader.agent_name == "LEADER_LOW"

    def test_leader_low_build_prompt(self, tmp_path):
        from agents.leader import LeaderLow
        cfg = {"model": "deepseek-v3", "max_tokens": 8192, "temperature": 0.3}
        with patch("agents.base_agent.OpenAI"), \
             patch("agents.leader.config") as mc:
            mc.get_worker.return_value = cfg
            leader = LeaderLow()
        result = leader._build_prompt({"task": "simple fix"})
        assert isinstance(result, str) and len(result) > 0

    def test_leader_high_init(self, tmp_path):
        from agents.leader import LeaderHigh
        cfg = {"model": "gemini-3.1-pro", "max_tokens": 16384, "temperature": 0.3}
        with patch("agents.base_agent.OpenAI"), \
             patch("agents.leader.config") as mc:
            mc.get_worker.return_value = cfg
            leader = LeaderHigh()
        assert leader.agent_name == "LEADER_HIGH"

    def test_leader_high_build_prompt(self, tmp_path):
        from agents.leader import LeaderHigh
        cfg = {"model": "gemini-3.1-pro", "max_tokens": 16384, "temperature": 0.3}
        with patch("agents.base_agent.OpenAI"), \
             patch("agents.leader.config") as mc:
            mc.get_worker.return_value = cfg
            leader = LeaderHigh()
        result = leader._build_prompt({"task": "architecture design"})
        assert isinstance(result, str) and len(result) > 0
