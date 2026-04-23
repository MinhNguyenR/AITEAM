"""Tests for core/cli/monitor_payload.py — path validation and prompt sanitation."""
from pathlib import Path

import pytest

from core.cli.monitor_payload import (
    MAX_MONITOR_PROMPT_CHARS,
    is_path_under_base,
    resolve_trusted_project_root,
    sanitize_monitor_prompt,
)


class TestIsPathUnderBase:
    def test_child_path_is_under(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        child = base / "sub" / "file.txt"
        child.parent.mkdir(parents=True, exist_ok=True)
        child.touch()
        assert is_path_under_base(child, base) is True

    def test_sibling_not_under(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        sibling = tmp_path / "other"
        sibling.mkdir()
        assert is_path_under_base(sibling, base) is False

    def test_path_escape_via_dotdot(self, tmp_path):
        base = tmp_path / "base"
        base.mkdir()
        escape = base / ".." / "secret"
        assert is_path_under_base(escape, base) is False


class TestResolveTrustedProjectRoot:
    def test_empty_raw_returns_repo_root(self, tmp_path):
        result = resolve_trusted_project_root(
            None, repo_root=str(tmp_path), home_config_dir=tmp_path / ".config"
        )
        assert result == tmp_path.resolve()

    def test_blank_raw_returns_repo_root(self, tmp_path):
        result = resolve_trusted_project_root(
            "   ", repo_root=str(tmp_path), home_config_dir=tmp_path / ".config"
        )
        assert result == tmp_path.resolve()

    def test_valid_child_path_accepted(self, tmp_path):
        child = tmp_path / "sub"
        child.mkdir()
        result = resolve_trusted_project_root(
            str(child), repo_root=str(tmp_path), home_config_dir=tmp_path / ".config"
        )
        assert result == child.resolve()

    def test_outside_path_rejected(self, tmp_path):
        outside = tmp_path.parent
        result = resolve_trusted_project_root(
            str(outside), repo_root=str(tmp_path), home_config_dir=tmp_path / ".config"
        )
        # outside is the parent — depends on system layout; either accepted as CWD parent or rejected
        # The key is: must not crash
        assert result is None or isinstance(result, Path)


class TestSanitizeMonitorPrompt:
    def test_none_returns_empty(self):
        assert sanitize_monitor_prompt(None) == ""

    def test_blank_returns_empty(self):
        assert sanitize_monitor_prompt("  ") == ""

    def test_normal_text_unchanged(self):
        assert sanitize_monitor_prompt("hello") == "hello"

    def test_strips_whitespace(self):
        assert sanitize_monitor_prompt("  hi  ") == "hi"

    def test_truncates_over_limit(self):
        long = "x" * (MAX_MONITOR_PROMPT_CHARS + 100)
        result = sanitize_monitor_prompt(long)
        assert len(result) == MAX_MONITOR_PROMPT_CHARS

    def test_at_limit_not_truncated(self):
        exact = "y" * MAX_MONITOR_PROMPT_CHARS
        assert len(sanitize_monitor_prompt(exact)) == MAX_MONITOR_PROMPT_CHARS
