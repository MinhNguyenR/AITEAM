"""Tests for core/config/registry/ — model registry and tier mapping."""
from core.config.registry import (
    MODEL_REGISTRY,
    TIER_MODEL_MAP,
    get_model_for_tier,
    get_worker_config,
)


class TestGetWorkerConfig:
    def test_ambassador_exists(self):
        cfg = get_worker_config("AMBASSADOR")
        assert cfg is not None
        assert "model" in cfg

    def test_leader_low_exists(self):
        cfg = get_worker_config("LEADER_LOW")
        assert cfg is not None

    def test_case_insensitive(self):
        cfg1 = get_worker_config("ambassador")
        cfg2 = get_worker_config("AMBASSADOR")
        assert cfg1 == cfg2

    def test_missing_returns_none(self):
        assert get_worker_config("NONEXISTENT_AGENT_XYZ") is None

    def test_config_has_required_keys(self):
        for key in ("AMBASSADOR", "LEADER_LOW", "LEADER_MEDIUM", "EXPERT"):
            cfg = get_worker_config(key)
            assert cfg is not None
            assert "model" in cfg
            assert "max_tokens" in cfg
            assert "temperature" in cfg


class TestGetModelForTier:
    def test_low_tier(self):
        model = get_model_for_tier("LOW")
        assert isinstance(model, str)
        assert len(model) > 0

    def test_medium_tier(self):
        model = get_model_for_tier("MEDIUM")
        assert isinstance(model, str)

    def test_unknown_expert_tier_falls_back_to_medium(self):
        model = get_model_for_tier("EXPERT")
        assert isinstance(model, str)
        assert model == TIER_MODEL_MAP["MEDIUM"]

    def test_hard_tier(self):
        model = get_model_for_tier("HARD")
        assert isinstance(model, str)

    def test_case_insensitive(self):
        assert get_model_for_tier("low") == get_model_for_tier("LOW")

    def test_unknown_tier_returns_medium_default(self):
        result = get_model_for_tier("UNKNOWN_TIER")
        assert result == TIER_MODEL_MAP["MEDIUM"]


class TestModelRegistry:
    def test_all_required_agents_present(self):
        required = ["AMBASSADOR", "LEADER_LOW", "LEADER_MEDIUM", "LEADER_HIGH", "EXPERT"]
        for agent in required:
            assert agent in MODEL_REGISTRY, f"Missing {agent}"

    def test_all_entries_have_model_field(self):
        for key, cfg in MODEL_REGISTRY.items():
            assert "model" in cfg, f"{key} missing model field"

    def test_tier_model_map_covers_all_tiers(self):
        for tier in ("LOW", "MEDIUM", "HARD"):
            assert tier in TIER_MODEL_MAP
