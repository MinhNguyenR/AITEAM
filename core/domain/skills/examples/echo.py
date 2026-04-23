"""Example skill module — one file per skill at scale."""

from __future__ import annotations

from .._registry import SkillSpec, register

ECHO_SKILL = SkillSpec(
    id="example.echo",
    name="Echo",
    description="Placeholder skill for registry tests and copy-paste scaffolding.",
    tags=("example", "builtin"),
    prompt_fragment=None,
)

register(ECHO_SKILL)
