"""Agent skill catalog with auto-discovery for builtin/custom modules."""

from __future__ import annotations

from ._loader import auto_discover
from ._registry import (
    SkillSpec,
    ToolSpec,
    all_skill_ids,
    get_skill,
    iter_by_category,
    iter_by_tag,
    iter_skills,
    register,
    search_skills,
)
from .hooks import prompt_fragment_for_skill

auto_discover()

__all__ = [
    "SkillSpec",
    "ToolSpec",
    "all_skill_ids",
    "get_skill",
    "iter_by_category",
    "iter_by_tag",
    "iter_skills",
    "prompt_fragment_for_skill",
    "register",
    "search_skills",
]
