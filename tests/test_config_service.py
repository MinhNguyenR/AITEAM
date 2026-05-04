"""Tests for core/config/service.py — Config class methods."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture()
def cfg(monkeypatch):
    """Provide a fresh Config singleton with all heavy I/O mocked out."""
    from core.config.service import Config

    old_instance = Config._instance
    old_scanned = Config._hardware_scanned
    old_device = Config._device
    old_gpu = Config._gpu_name
    old_vram = Config._total_vram_gb
    old_ram = Config._total_ram_gb
    old_limit = Config._max_vram_limit

    Config._instance = None
    Config._hardware_scanned = False
    Config._device = "cpu"
    Config._gpu_name = "Unknown"
    Config._total_vram_gb = 0.0
    Config._total_ram_gb = 0.0
    Config._max_vram_limit = None

    with patch("core.config.service.load_environment"), \
         patch("core.config.service.require_openrouter_api_key"), \
         patch("core.config.service.detect_gpu_info", return_value=("cuda", "RTX 4090", 24.0)), \
         patch("core.config.service.detect_total_ram_gb", return_value=32.0), \
         patch("core.config.service.fetch_openrouter_pricing", return_value=({}, True)), \
         patch("core.config.service.sync_live_pricing"):
        instance = Config()

    yield instance

    Config._instance = old_instance
    Config._hardware_scanned = old_scanned
    Config._device = old_device
    Config._gpu_name = old_gpu
    Config._total_vram_gb = old_vram
    Config._total_ram_gb = old_ram
    Config._max_vram_limit = old_limit


class TestConfigProperties:
    def test_gpu_name(self, cfg):
        assert cfg.gpu_name == "RTX 4090"

    def test_total_vram_gb_no_limit(self, cfg):
        assert cfg.total_vram_gb == 24.0

    def test_total_vram_gb_with_user_limit(self, cfg):
        from core.config.service import Config
        Config._max_vram_limit = 12.0
        assert cfg.total_vram_gb == 12.0
        Config._max_vram_limit = None

    def test_total_ram_gb(self, cfg):
        assert cfg.total_ram_gb == 32.0

    def test_device(self, cfg):
        assert cfg.device == "cuda"

    def test_available_vram_is_80_percent(self, cfg):
        assert cfg.available_vram_gb == pytest.approx(24.0 * 0.8)

    def test_api_key_masked(self, cfg, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-1234")
        result = cfg.api_key_masked
        assert "1234" in result or "****" in result

    def test_api_key(self, cfg, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
        assert cfg.api_key == "sk-test-key"

    def test_cache_root_default(self, cfg, monkeypatch):
        monkeypatch.delenv("AI_TEAM_CACHE_ROOT", raising=False)
        root = cfg.cache_root
        assert "aiteam-cache" in str(root)

    def test_cache_root_custom(self, cfg, monkeypatch):
        monkeypatch.setenv("AI_TEAM_CACHE_ROOT", "/tmp/custom-cache")
        root = cfg.cache_root
        assert "custom-cache" in str(root)


class TestGetWorker:
    def test_returns_none_for_unknown_worker(self, cfg):
        result = cfg.get_worker("NONEXISTENT_WORKER_XYZ")
        assert result is None

    def test_returns_dict_for_valid_worker(self, cfg):
        with patch("core.app_state.get_model_overrides", return_value={}), \
             patch("core.app_state.get_prompt_overrides", return_value={}):
            result = cfg.get_worker("LEADER_MEDIUM")
        assert result is not None
        assert "model" in result

    def test_applies_model_override(self, cfg):
        with patch("core.app_state.get_model_overrides", return_value={"LEADER_MEDIUM": "custom-model"}), \
             patch("core.app_state.get_prompt_overrides", return_value={}):
            result = cfg.get_worker("LEADER_MEDIUM")
        assert result["model"] == "custom-model"
        assert result["is_overridden"] is True

    def test_import_error_sets_not_overridden(self, cfg):
        with patch.dict("sys.modules", {"core.app_state": None}):
            result = cfg.get_worker("LEADER_MEDIUM")
        assert result is not None
        assert result["is_overridden"] is False


class TestGetModelForTier:
    def test_returns_string(self, cfg):
        result = cfg.get_model_for_tier("MEDIUM")
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetFallbackWorker:
    def test_worker_a_falls_back_to_c(self, cfg):
        assert cfg.get_fallback_worker("WORKER_A") == "WORKER_C"

    def test_worker_b_falls_back_to_c(self, cfg):
        assert cfg.get_fallback_worker("WORKER_B") == "WORKER_C"

    def test_unknown_falls_back_to_fix(self, cfg):
        assert cfg.get_fallback_worker("LEADER_HIGH") == "FIX_WORKER"


class TestListWorkers:
    def test_returns_list(self, cfg):
        with patch("core.app_state.get_model_overrides", return_value={}), \
             patch("core.app_state.get_prompt_overrides", return_value={}):
            result = cfg.list_workers()
        assert isinstance(result, list)
        assert len(result) > 0

    def test_each_entry_has_required_keys(self, cfg):
        with patch("core.app_state.get_model_overrides", return_value={}), \
             patch("core.app_state.get_prompt_overrides", return_value={}):
            result = cfg.list_workers()
        for entry in result:
            assert "id" in entry
            assert "model" in entry
            assert "role" in entry

    def test_import_error_uses_empty_overrides(self, cfg):
        with patch.dict("sys.modules", {"core.app_state": None}):
            result = cfg.list_workers()
        assert isinstance(result, list)


class TestListAgentsByTier:
    def test_returns_list(self, cfg):
        result = cfg.list_agents_by_tier(1)
        assert isinstance(result, list)


class TestGetPricingSummary:
    def test_returns_dict(self, cfg):
        result = cfg.get_pricing_summary()
        assert isinstance(result, dict)

    def test_free_models_labeled(self, cfg):
        result = cfg.get_pricing_summary()
        for val in result.values():
            assert isinstance(val, str)


class TestGetLivePricing:
    def test_returns_cached_value(self, cfg):
        from core.config.service import Config
        Config._pricing_cache = {"test-model": {"input": 1.0, "output": 2.0}}
        result = cfg.get_live_pricing("test-model")
        assert result["input"] == 1.0
        Config._pricing_cache = {}

    def test_falls_back_to_registry(self, cfg):
        from core.config.service import Config
        Config._pricing_cache = {}
        result = cfg.get_live_pricing("totally-unknown-model-xyz")
        assert "input" in result
        assert "output" in result


class TestGetHardwareString:
    def test_returns_string(self, cfg):
        result = cfg.get_hardware_string()
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetSystemInfo:
    def test_returns_hardware_block(self, cfg):
        result = cfg.get_system_info()
        assert "hardware" in result
        assert "gpu" in result["hardware"]

    def test_returns_api_block(self, cfg, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test")
        result = cfg.get_system_info()
        assert "api" in result
        assert "key_masked" in result["api"]

    def test_agents_count(self, cfg):
        result = cfg.get_system_info()
        assert result["agents"]["total"] > 0


class TestApplyUserOverrides:
    def test_vram_limit_applied(self, monkeypatch):
        from core.config.service import Config
        old_instance = Config._instance
        old_scanned = Config._hardware_scanned
        Config._instance = None
        Config._hardware_scanned = False
        Config._max_vram_limit = None

        monkeypatch.setenv("MAX_VRAM_LIMIT", "16.0")

        with patch("core.config.service.load_environment"), \
             patch("core.config.service.require_openrouter_api_key"), \
             patch("core.config.service.detect_gpu_info", return_value=("cpu", "CPU", 0.0)), \
             patch("core.config.service.detect_total_ram_gb", return_value=16.0), \
             patch("core.config.service.fetch_openrouter_pricing", return_value=({}, True)), \
             patch("core.config.service.sync_live_pricing"):
            instance = Config()

        assert Config._max_vram_limit == 16.0

        Config._instance = old_instance
        Config._hardware_scanned = old_scanned
        Config._max_vram_limit = None
