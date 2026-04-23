"""Tests for core/cli/state.py — settings, context state, overrides."""
import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

import core.cli.state as state_mod


def _reset_settings_cache():
    """Reset module-level cache so each test starts fresh."""
    state_mod._cli_settings = None


# ---------------------------------------------------------------------------
# load_cli_settings
# ---------------------------------------------------------------------------

class TestLoadCliSettings:
    def test_returns_defaults_when_no_files(self, tmp_path):
        with patch.object(state_mod, "_SETTINGS_FILE", tmp_path / "nonexistent.json"), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "legacy.json"):
            result = state_mod.load_cli_settings()
        assert result["theme"] == "dark"
        assert result["over_budget_continue"] is False

    def test_loads_settings_file(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps({"theme": "light"}), encoding="utf-8")
        with patch.object(state_mod, "_SETTINGS_FILE", sf), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "legacy.json"):
            result = state_mod.load_cli_settings()
        assert result["theme"] == "light"

    def test_workflow_view_mode_defaults_to_chain(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps({}), encoding="utf-8")
        with patch.object(state_mod, "_SETTINGS_FILE", sf), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "legacy.json"):
            result = state_mod.load_cli_settings()
        assert result["workflow_view_mode"] == "chain"

    def test_workflow_view_mode_list(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text(json.dumps({"workflow_view_mode": "list"}), encoding="utf-8")
        with patch.object(state_mod, "_SETTINGS_FILE", sf), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "legacy.json"):
            result = state_mod.load_cli_settings()
        assert result["workflow_view_mode"] == "list"

    def test_corrupt_settings_returns_defaults(self, tmp_path):
        sf = tmp_path / "settings.json"
        sf.write_text("NOT JSON", encoding="utf-8")
        with patch.object(state_mod, "_SETTINGS_FILE", sf), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "legacy.json"):
            result = state_mod.load_cli_settings()
        assert result["theme"] == "dark"

    def test_defaults_contain_required_keys(self, tmp_path):
        with patch.object(state_mod, "_SETTINGS_FILE", tmp_path / "nope.json"), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "nope2.json"):
            result = state_mod.load_cli_settings()
        for key in ("theme", "auto_accept_context", "daily_budget_usd", "over_budget_continue"):
            assert key in result


class TestGetCliSettings:
    def test_returns_dict_copy(self, tmp_path):
        _reset_settings_cache()
        with patch.object(state_mod, "_SETTINGS_FILE", tmp_path / "nope.json"), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "nope2.json"):
            s1 = state_mod.get_cli_settings()
            s2 = state_mod.get_cli_settings()
        assert s1 is not s2  # must be a copy

    def test_concurrent_access_safe(self, tmp_path):
        _reset_settings_cache()
        errors = []
        with patch.object(state_mod, "_SETTINGS_FILE", tmp_path / "nope.json"), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "nope2.json"):
            def worker():
                try:
                    state_mod.get_cli_settings()
                except Exception as e:
                    errors.append(e)
            threads = [threading.Thread(target=worker) for _ in range(10)]
            for t in threads: t.start()
            for t in threads: t.join()
        assert errors == []


# ---------------------------------------------------------------------------
# save_cli_settings
# ---------------------------------------------------------------------------

class TestSaveCliSettings:
    def test_round_trips(self, tmp_path):
        _reset_settings_cache()
        sf = tmp_path / "settings.json"
        with patch.object(state_mod, "_SETTINGS_FILE", sf), \
             patch.object(state_mod, "_LEGACY_SETTINGS_FILE", tmp_path / "legacy.json"):
            state_mod.save_cli_settings({"theme": "light", "over_budget_continue": True})
            loaded = json.loads(sf.read_text(encoding="utf-8"))
        assert loaded["theme"] == "light"
        assert loaded["over_budget_continue"] is True


# ---------------------------------------------------------------------------
# load_context_state / save_context_state
# ---------------------------------------------------------------------------

class TestContextState:
    def test_returns_empty_dict_when_no_file(self, tmp_path):
        with patch.object(state_mod, "_context_state_path", return_value=tmp_path / "ctx.json"):
            result = state_mod.load_context_state()
        assert result == {}

    def test_save_and_load_roundtrip(self, tmp_path):
        ctx_path = tmp_path / "context_state.json"
        with patch.object(state_mod, "_context_state_path", return_value=ctx_path):
            state_mod.save_context_state({"status": "active", "task_uuid": "abc"})
            result = state_mod.load_context_state()
        assert result["status"] == "active"
        assert result["task_uuid"] == "abc"

    def test_corrupt_context_state_returns_empty(self, tmp_path):
        ctx_path = tmp_path / "context_state.json"
        ctx_path.write_text("BAD JSON", encoding="utf-8")
        with patch.object(state_mod, "_context_state_path", return_value=ctx_path):
            result = state_mod.load_context_state()
        assert result == {}

    def test_is_context_active(self, tmp_path):
        ctx_path = tmp_path / "context_state.json"
        with patch.object(state_mod, "_context_state_path", return_value=ctx_path):
            state_mod.save_context_state({"status": "active"})
            assert state_mod.is_context_active() is True

    def test_is_context_not_active(self, tmp_path):
        ctx_path = tmp_path / "context_state.json"
        with patch.object(state_mod, "_context_state_path", return_value=ctx_path):
            state_mod.save_context_state({"status": "inactive"})
            assert state_mod.is_context_active() is False


# ---------------------------------------------------------------------------
# model/prompt overrides
# ---------------------------------------------------------------------------

class TestModelOverrides:
    def test_returns_empty_when_no_file(self, tmp_path):
        with patch.object(state_mod, "_OVERRIDES_FILE", tmp_path / "overrides.json"):
            result = state_mod.get_model_overrides()
        assert result == {}

    def test_set_and_get_override(self, tmp_path):
        ovf = tmp_path / "overrides.json"
        with patch.object(state_mod, "_OVERRIDES_FILE", ovf):
            state_mod.set_model_override("AMBASSADOR", "new-model")
            result = state_mod.get_model_overrides()
        assert result["AMBASSADOR"] == "new-model"
