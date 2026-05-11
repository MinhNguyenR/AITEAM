"""Central skill registry. Add new skills in subpackages and call register() from each module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

_SKILLS: dict[str, "SkillSpec"] = {}


@dataclass(frozen=True, slots=True)
class SkillSpec:
    id: str
    name: str
    description: str
    category: str = "general"
    version: str = "1.0.0"
    tags: tuple[str, ...] = ()
    prompt_fragment: str | None = None
    callable: Callable | None = None
    input_schema: dict | None = None
    output_schema: dict | None = None


ToolSpec = SkillSpec


def register(spec: SkillSpec) -> None:
    if spec.id in _SKILLS:
        raise ValueError(f"duplicate skill id: {spec.id!r}")
    _SKILLS[spec.id] = spec


def get_skill(skill_id: str) -> SkillSpec | None:
    return _SKILLS.get(skill_id)


def iter_skills() -> Iterator[SkillSpec]:
    return iter(sorted(_SKILLS.values(), key=lambda s: s.id))


def iter_by_category(category: str) -> Iterator[SkillSpec]:
    wanted = str(category or "").lower()
    return (s for s in iter_skills() if s.category.lower() == wanted)


def iter_by_tag(tag: str) -> Iterator[SkillSpec]:
    wanted = str(tag or "").lower()
    return (s for s in iter_skills() if wanted in {t.lower() for t in s.tags})


def search_skills(query: str) -> list[SkillSpec]:
    q = str(query or "").lower().strip()
    if not q:
        return list(iter_skills())
    return [
        s for s in iter_skills()
        if q in s.id.lower()
        or q in s.name.lower()
        or q in s.description.lower()
        or any(q in tag.lower() for tag in s.tags)
    ]


def all_skill_ids() -> frozenset[str]:
    return frozenset(_SKILLS.keys())


__all__ = [
    "SkillSpec",
    "ToolSpec",
    "all_skill_ids",
    "get_skill",
    "iter_by_category",
    "iter_by_tag",
    "iter_skills",
    "register",
    "search_skills",
]
