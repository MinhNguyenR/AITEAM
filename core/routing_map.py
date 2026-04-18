"""Single source of truth: task tier → leader registry key + DeltaBrief.selected_leader."""

from __future__ import annotations

from typing import Tuple

# tier -> (config.get_worker key, DeltaBrief.selected_leader)
_TIER_ROUTE: dict[str, Tuple[str, str]] = {
    "LOW": ("LEADER_MEDIUM", "LEADER_MEDIUM"),
    "MEDIUM": ("LEADER_MEDIUM", "LEADER_MEDIUM"),
    "EXPERT": ("EXPERT", "EXPERT_MIMO"),
    "HARD": ("LEADER_HIGH", "LEADER_HIGH"),
}
_DEFAULT_REG = "LEADER_MEDIUM"
_DEFAULT_LEADER = "LEADER_MEDIUM"


def _norm_tier(tier: str) -> str:
    return (tier or "").strip().upper()


def pipeline_registry_key_for_tier(tier: str) -> str:
    return _TIER_ROUTE.get(_norm_tier(tier), (_DEFAULT_REG, _DEFAULT_LEADER))[0]


def selected_leader_for_tier(tier: str) -> str:
    return _TIER_ROUTE.get(_norm_tier(tier), (_DEFAULT_REG, _DEFAULT_LEADER))[1]


__all__ = ["pipeline_registry_key_for_tier", "selected_leader_for_tier"]
