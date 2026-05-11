"""Single source of truth: task tier -> leader registry key, DeltaBrief.selected_leader, pipeline node order.

When routing by declared skills, consult `core.domain.skills` registry / `hooks.prompt_fragment_for_skill`.
"""

from __future__ import annotations

from typing import Tuple

_TIER_ROUTE: dict[str, Tuple[str, str]] = {
    "LOW":    ("LEADER_LOW",    "LEADER_LOW"),
    "MEDIUM": ("LEADER_MEDIUM", "LEADER_MEDIUM"),
    "HARD":   ("LEADER_HIGH",   "LEADER_HIGH"),
}
_DEFAULT_REG = "LEADER_MEDIUM"
_DEFAULT_LEADER = "LEADER_MEDIUM"

_PIPELINE_NODES_DEFAULT: tuple[str, ...] = (
    "ambassador",
    "leader_generate",
    "human_context_gate",
    "parallel_prepare",
    "secretary_setup",
    "tool_curator",
    "worker_a",
    "worker_b",
    "worker_c",
    "worker_d",
    "worker_e",
    "parallel_join",
    "secretary",
    "finalize_phase1",
)
_PIPELINE_NODES_BY_TIER: dict[str, tuple[str, ...]] = {
    "LOW":    _PIPELINE_NODES_DEFAULT,
    "MEDIUM": _PIPELINE_NODES_DEFAULT,
    "HARD":   _PIPELINE_NODES_DEFAULT,
}


def _norm_tier(tier: str) -> str:
    return (tier or "").strip().upper()


def pipeline_registry_key_for_tier(tier: str) -> str:
    return _TIER_ROUTE.get(_norm_tier(tier), (_DEFAULT_REG, _DEFAULT_LEADER))[0]


def selected_leader_for_tier(tier: str) -> str:
    return _TIER_ROUTE.get(_norm_tier(tier), (_DEFAULT_REG, _DEFAULT_LEADER))[1]


def pipeline_nodes_for_tier(tier: str | None) -> list[str]:
    return list(_PIPELINE_NODES_BY_TIER.get(_norm_tier(tier or ""), _PIPELINE_NODES_DEFAULT))


__all__ = [
    "pipeline_registry_key_for_tier",
    "selected_leader_for_tier",
    "pipeline_nodes_for_tier",
]
