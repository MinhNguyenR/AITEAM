"""Central skill registry. Add new skills in subpackages and call register() from each module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

_SKILLS: dict[str, "SkillSpec"] = {}


@dataclass(frozen=True, slots=True)
class SkillSpec:
    id: str
    name: str
    description: str
    tags: tuple[str, ...] = ()
    prompt_fragment: str | None = None


def register(spec: SkillSpec) -> None:
    if spec.id in _SKILLS:
        raise ValueError(f"duplicate skill id: {spec.id!r}")
    _SKILLS[spec.id] = spec


def get_skill(skill_id: str) -> SkillSpec | None:
    return _SKILLS.get(skill_id)


def iter_skills() -> Iterator[SkillSpec]:
    return iter(sorted(_SKILLS.values(), key=lambda s: s.id))


def all_skill_ids() -> frozenset[str]:
    return frozenset(_SKILLS.keys())
