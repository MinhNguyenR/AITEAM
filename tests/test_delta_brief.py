"""Tests for utils/delta_brief.py — DeltaBrief model and helpers."""
import pytest
from pathlib import Path
from pydantic import ValidationError

from utils.delta_brief import (
    DeltaBrief,
    build_state_payload,
    is_no_context,
    NO_CONTEXT_HEADER,
)


class TestDeltaBriefValidation:
    def _valid_kwargs(self, **overrides):
        base = {
            "original_prompt": "build a REST API",
            "summary": "build REST API",
            "tier": "LOW",
            "target_model": "test-model",
            "selected_leader": "LEADER_LOW",
        }
        base.update(overrides)
        return base

    def test_valid_low_tier(self):
        b = DeltaBrief(**self._valid_kwargs())
        assert b.tier == "LOW"

    def test_tier_uppercased(self):
        b = DeltaBrief(**self._valid_kwargs(tier="medium"))
        assert b.tier == "MEDIUM"

    def test_invalid_tier_raises(self):
        with pytest.raises(ValidationError):
            DeltaBrief(**self._valid_kwargs(tier="SUPER"))

    def test_all_valid_tiers(self):
        for tier in ("LOW", "MEDIUM", "EXPERT", "HARD"):
            b = DeltaBrief(**self._valid_kwargs(tier=tier))
            assert b.tier == tier

    def test_invalid_leader_raises(self):
        with pytest.raises(ValidationError):
            DeltaBrief(**self._valid_kwargs(selected_leader="UNKNOWN_LEADER"))

    def test_all_valid_leaders(self):
        for leader in ("LEADER_LOW", "LEADER_MEDIUM", "EXPERT_MIMO", "LEADER_HIGH"):
            b = DeltaBrief(**self._valid_kwargs(selected_leader=leader))
            assert b.selected_leader == leader

    def test_complexity_score_bounds(self):
        b = DeltaBrief(**self._valid_kwargs(complexity_score=0.5))
        assert b.complexity_score == 0.5

    def test_complexity_score_out_of_range(self):
        with pytest.raises(ValidationError):
            DeltaBrief(**self._valid_kwargs(complexity_score=1.5))

    def test_task_uuid_auto_generated(self):
        b = DeltaBrief(**self._valid_kwargs())
        assert len(b.task_uuid) == 36  # UUID4 length

    def test_timestamp_auto_generated(self):
        b = DeltaBrief(**self._valid_kwargs())
        assert "T" in b.timestamp  # ISO format

    def test_optional_vram(self):
        b = DeltaBrief(**self._valid_kwargs(estimated_vram_usage="16GB"))
        assert b.estimated_vram_usage == "16GB"

    def test_default_no_vram(self):
        b = DeltaBrief(**self._valid_kwargs())
        assert b.estimated_vram_usage is None


class TestBuildStatePayload:
    def _brief(self, **kw):
        base = {
            "original_prompt": "test prompt",
            "summary": "test",
            "tier": "LOW",
            "target_model": "model",
            "selected_leader": "LEADER_LOW",
        }
        base.update(kw)
        return DeltaBrief(**base)

    def test_state_has_required_keys(self):
        brief = self._brief()
        payload = build_state_payload(brief, "test prompt", {})
        assert set(payload) >= {"task_uuid", "original_prompt", "tier", "language", "complexity", "is_cuda", "constraints", "hardware"}

    def test_cuda_adds_constraint(self):
        brief = self._brief(is_cuda_required=True, tier="HARD", selected_leader="LEADER_HIGH")
        payload = build_state_payload(brief, "prompt", {})
        assert "CUDA required" in payload["constraints"]

    def test_vram_adds_constraint(self):
        brief = self._brief(estimated_vram_usage="8GB")
        payload = build_state_payload(brief, "prompt", {})
        assert any("VRAM" in c for c in payload["constraints"])

    def test_no_cuda_no_constraint(self):
        brief = self._brief()
        payload = build_state_payload(brief, "prompt", {})
        assert not any("CUDA" in c for c in payload["constraints"])

    def test_hardware_info_included(self):
        hw = {"gpu": "RTX 4090", "vram": "24GB"}
        brief = self._brief()
        payload = build_state_payload(brief, "prompt", hw)
        assert payload["hardware"] == hw


class TestIsNoContext:
    def test_nonexistent_file_is_no_context(self, tmp_path):
        assert is_no_context(tmp_path / "missing.md") is True

    def test_file_with_no_context_header(self, tmp_path):
        f = tmp_path / "context.md"
        f.write_text(f"{NO_CONTEXT_HEADER}\nSome content", encoding="utf-8")
        assert is_no_context(f) is True

    def test_file_with_real_content(self, tmp_path):
        f = tmp_path / "context.md"
        f.write_text("# Real architecture plan\n## Tasks", encoding="utf-8")
        assert is_no_context(f) is False

    def test_empty_file_is_no_context(self, tmp_path):
        f = tmp_path / "context.md"
        f.write_text("", encoding="utf-8")
        assert is_no_context(f) is True
