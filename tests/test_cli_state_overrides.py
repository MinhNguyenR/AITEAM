"""Tests for core/cli/state.py — model/prompt/sampling overrides and context state."""
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import core.cli.state as state_mod


def _tmp_overrides(tmp_path: Path):
    """Return a patcher for _OVERRIDES_FILE pointing to a temp file."""
    return patch.object(state_mod, "_OVERRIDES_FILE", tmp_path / "model_overrides.json")


def _tmp_context_path(tmp_path: Path):
    """Return a patcher for _context_state_path to use tmp dir."""
    ctx_file = tmp_path / "context_state.json"
    mock_fn = MagicMock(return_value=ctx_file)
    return patch.object(state_mod, "_context_state_path", mock_fn)


class TestModelOverrides:
    def test_get_empty_when_no_file(self, tmp_path):
        with _tmp_overrides(tmp_path):
            result = state_mod.get_model_overrides()
        assert result == {}

    def test_set_and_get_model_override(self, tmp_path):
        with _tmp_overrides(tmp_path), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.set_model_override("AMBASSADOR", "claude-3-haiku")
            result = state_mod.get_model_overrides()
        assert result["AMBASSADOR"] == "claude-3-haiku"

    def test_reset_model_override(self, tmp_path):
        with _tmp_overrides(tmp_path), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.set_model_override("LEADER", "gpt-4")
            state_mod.reset_model_override("LEADER")
            result = state_mod.get_model_overrides()
        assert "LEADER" not in result


class TestPromptOverrides:
    def test_get_empty_when_no_file(self, tmp_path):
        with _tmp_overrides(tmp_path):
            result = state_mod.get_prompt_overrides()
        assert result == {}

    def test_set_and_get_prompt_override(self, tmp_path):
        with _tmp_overrides(tmp_path), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.set_prompt_override("EXPERT", "Custom prompt text here")
            result = state_mod.get_prompt_overrides()
        assert "EXPERT" in result
        assert result["EXPERT"]["prompt"] == "Custom prompt text here"
        assert "updated_at" in result["EXPERT"]

    def test_reset_prompt_override(self, tmp_path):
        with _tmp_overrides(tmp_path), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.set_prompt_override("LEADER", "My prompt")
            state_mod.reset_prompt_override("LEADER")
            result = state_mod.get_prompt_overrides()
        assert "LEADER" not in result


class TestSamplingOverrides:
    def test_get_empty_when_no_file(self, tmp_path):
        with _tmp_overrides(tmp_path):
            result = state_mod.get_sampling_overrides()
        assert result == {}

    def test_update_temperature(self, tmp_path):
        with _tmp_overrides(tmp_path), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.update_sampling_override("AMBASSADOR", temperature=0.3)
            result = state_mod.get_sampling_overrides()
        assert result.get("AMBASSADOR", {}).get("temperature") == 0.3

    def test_ignores_none_values(self, tmp_path):
        with _tmp_overrides(tmp_path), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.update_sampling_override("LEADER", temperature=None)
            result = state_mod.get_sampling_overrides()
        assert "temperature" not in result.get("LEADER", {})


class TestResetAllRoleOverrides:
    def test_resets_both_model_and_prompt(self, tmp_path):
        with _tmp_overrides(tmp_path), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.set_model_override("EXPERT", "gpt-4")
            state_mod.set_prompt_override("EXPERT", "My custom prompt")
            state_mod.reset_all_role_overrides("EXPERT")
            models = state_mod.get_model_overrides()
            prompts = state_mod.get_prompt_overrides()
        assert "EXPERT" not in models
        assert "EXPERT" not in prompts


class TestLoadOverridesBrokenJson:
    def test_returns_defaults_on_decode_error(self, tmp_path):
        overrides_file = tmp_path / "model_overrides.json"
        overrides_file.write_text("not valid json{{", encoding="utf-8")
        with patch.object(state_mod, "_OVERRIDES_FILE", overrides_file):
            result = state_mod._load_overrides()
        assert "model_overrides" in result
        assert result["model_overrides"] == {}


class TestContextState:
    def test_load_returns_empty_when_no_file(self, tmp_path):
        with _tmp_context_path(tmp_path):
            result = state_mod.load_context_state()
        assert result == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        ctx_file = tmp_path / "context_state.json"
        with patch.object(state_mod, "_context_state_path", MagicMock(return_value=ctx_file)):
            state_mod.save_context_state({"status": "active", "task_uuid": "abc"})
            result = state_mod.load_context_state()
        assert result["status"] == "active"
        assert result["task_uuid"] == "abc"

    def test_load_returns_empty_on_corrupt_json(self, tmp_path):
        ctx_file = tmp_path / "context_state.json"
        ctx_file.write_text("bad json {{{", encoding="utf-8")
        with patch.object(state_mod, "_context_state_path", MagicMock(return_value=ctx_file)):
            result = state_mod.load_context_state()
        assert result == {}

    def test_is_context_active(self, tmp_path):
        ctx_file = tmp_path / "context_state.json"
        with patch.object(state_mod, "_context_state_path", MagicMock(return_value=ctx_file)):
            state_mod.save_context_state({"status": "active"})
            assert state_mod.is_context_active() is True
            state_mod.save_context_state({"status": "deleted"})
            assert state_mod.is_context_active() is False

    def test_update_context_state(self, tmp_path):
        ctx_file = tmp_path / "context_state.json"
        with patch.object(state_mod, "_context_state_path", MagicMock(return_value=ctx_file)), \
             patch.object(state_mod, "log_system_action", MagicMock()):
            state_mod.update_context_state("active", Path(tmp_path / "ctx.md"), "user", "task-123")
            result = state_mod.load_context_state()
        assert result["status"] == "active"
        assert result["task_uuid"] == "task-123"
