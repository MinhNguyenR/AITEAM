import pytest

from core.domain.skills import (
    SkillSpec,
    all_skill_ids,
    get_skill,
    iter_skills,
    prompt_fragment_for_skill,
    register,
)


def test_example_echo_registered():
    s = get_skill("example.echo")
    assert s is not None
    assert s.name == "Echo"
    assert "example" in s.tags


def test_duplicate_register_raises():
    with pytest.raises(ValueError, match="duplicate"):
        register(
            SkillSpec(
                id="example.echo",
                name="dup",
                description="x",
            )
        )


def test_iter_and_ids_sorted():
    ids = list(all_skill_ids())
    assert "example.echo" in ids
    listed = [s.id for s in iter_skills()]
    assert listed == sorted(listed)


def test_prompt_fragment_hook():
    assert prompt_fragment_for_skill("example.echo") is None
    assert prompt_fragment_for_skill("missing.skill.id") is None
