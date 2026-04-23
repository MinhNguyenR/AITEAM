"""Agent skill catalog: many modules under `examples/` or future domains; use register() per module."""

from __future__ import annotations

from . import examples  # noqa: F401 — register builtin skills
from ._registry import (
    SkillSpec,
    all_skill_ids,
    get_skill,
    iter_skills,
    register,
)
from .hooks import prompt_fragment_for_skill

__all__ = [
    "SkillSpec",
    "all_skill_ids",
    "get_skill",
    "iter_skills",
    "prompt_fragment_for_skill",
    "register",
]
