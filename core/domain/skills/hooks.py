"""Integration helpers for prompts and routing (extend when wiring agents)."""

from __future__ import annotations

from ._registry import get_skill


def prompt_fragment_for_skill(skill_id: str) -> str | None:
    spec = get_skill(skill_id)
    if spec is None:
        return None
    return spec.prompt_fragment
