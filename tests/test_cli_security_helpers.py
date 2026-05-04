from __future__ import annotations

from pathlib import Path

import pytest

from core.cli.python_cli.shell.monitor_payload import (
    MAX_MONITOR_PROMPT_CHARS,
    resolve_trusted_project_root,
    sanitize_monitor_prompt,
)
from core.cli.python_cli.shell.safe_editor import build_editor_argv


def test_build_editor_argv_rejects_injection(monkeypatch):
    p = Path("x.txt")
    monkeypatch.setenv("EDITOR", "vim; rm -rf /")
    argv = build_editor_argv(p)
    assert argv[0] != "vim"
    assert argv[-1] == str(p)


def test_build_editor_argv_splits_safe_editor(monkeypatch):
    p = Path("y.md")
    monkeypatch.setenv("EDITOR", "code -w")
    argv = build_editor_argv(p)
    assert argv[:-1] == ["code", "-w"]
    assert argv[-1] == str(p)


def test_resolve_trusted_project_root(tmp_path: Path):
    repo = tmp_path / "repo"
    sub = repo / "proj"
    sub.mkdir(parents=True)
    cfg = tmp_path / "cfg"
    cfg.mkdir()
    trusted = resolve_trusted_project_root(str(sub), repo_root=str(repo), home_config_dir=cfg)
    assert trusted == sub.resolve()
    outside = tmp_path / "other" / "x"
    outside.mkdir(parents=True)
    assert resolve_trusted_project_root(str(outside), repo_root=str(repo), home_config_dir=cfg) is None


def test_sanitize_monitor_prompt_truncates():
    long = "a" * (MAX_MONITOR_PROMPT_CHARS + 50)
    assert len(sanitize_monitor_prompt(long)) == MAX_MONITOR_PROMPT_CHARS


@pytest.mark.parametrize(
    "raw,expect_prefix",
    [
        (None, ""),
        ("  hi  ", "hi"),
    ],
)
def test_sanitize_monitor_prompt_strips(raw, expect_prefix):
    out = sanitize_monitor_prompt(raw)
    if expect_prefix:
        assert out == expect_prefix
    else:
        assert out == ""
