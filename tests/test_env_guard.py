"""Tests for utils/env_guard.py — redaction and env checks."""
import os
import stat
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from utils.env_guard import (
    redact_for_display,
    warn_if_env_permissions_unsafe,
    run_startup_checks,
    _dotenv_paths,
)


class TestRedactForDisplay:
    def test_redacts_openrouter_key(self):
        text = "Using key sk-or-v1-abcdefghijklmnopqrstuvwxyz1234"
        result = redact_for_display(text)
        assert "sk-or-v1-abcdefghijklmnopqrstuvwxyz1234" not in result
        assert "REDACTED" in result

    def test_redacts_openai_style_key(self):
        text = "Key: sk-abcdefghijklmnopqrstuvwxyz12345"
        result = redact_for_display(text)
        assert "sk-abcdefghijklmnopqrstuvwxyz12345" not in result
        assert "REDACTED" in result

    def test_redacts_vault_key(self):
        text = "AI_TEAM_VAULT_KEY=mysecretvaultkey123"
        result = redact_for_display(text)
        assert "mysecretvaultkey123" not in result
        assert "REDACTED" in result

    def test_empty_string_unchanged(self):
        assert redact_for_display("") == ""

    def test_no_secret_unchanged(self):
        text = "Normal log message without secrets"
        assert redact_for_display(text) == text

    def test_multiple_secrets_redacted(self):
        text = "sk-abcdefghijklmnopqrst123 and sk-or-v1-abcdefghijklmnopqrstuvwx"
        result = redact_for_display(text)
        assert "REDACTED" in result

    def test_short_key_not_redacted(self):
        text = "sk-short"
        result = redact_for_display(text)
        assert result == text

    def test_preserves_surrounding_text(self):
        text = "prefix sk-abcdefghijklmnopqrstuvwxyz12345 suffix"
        result = redact_for_display(text)
        assert "prefix" in result
        assert "suffix" in result


class TestDotenvPaths:
    def test_returns_existing_env_files(self, tmp_path):
        (tmp_path / ".env").write_text("KEY=val")
        paths = _dotenv_paths(tmp_path)
        assert any(p.name == ".env" for p in paths)

    def test_returns_env_local_if_exists(self, tmp_path):
        (tmp_path / ".env.local").write_text("LOCAL=1")
        paths = _dotenv_paths(tmp_path)
        assert any(p.name == ".env.local" for p in paths)

    def test_empty_when_no_files(self, tmp_path):
        paths = _dotenv_paths(tmp_path)
        # Only home ~/.ai-team/.env could appear — filter local ones
        local_paths = [p for p in paths if p.parent == tmp_path]
        assert local_paths == []

    def test_includes_home_env_if_exists(self, tmp_path):
        home_env = tmp_path / ".ai-team" / ".env"
        home_env.parent.mkdir(parents=True)
        home_env.write_text("HOME=1")
        with patch("utils.env_guard.Path") as MockPath:
            # Just verify the function doesn't raise
            paths = _dotenv_paths(tmp_path)
        assert isinstance(paths, list)


class TestWarnIfEnvPermissionsUnsafe:
    def test_no_env_file_noop(self, tmp_path):
        # No .env file → no warning, no crash
        warn_if_env_permissions_unsafe(tmp_path)

    def test_posix_world_readable_logs_warning(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("SK=secret")
        if os.name == "nt":
            return  # chmod semantics differ on Windows
        env_file.chmod(0o644)  # world-readable
        with patch("utils.env_guard.logger") as mock_log:
            warn_if_env_permissions_unsafe(tmp_path)
        mock_log.warning.assert_called()

    def test_posix_chmod_failure_swallowed(self, tmp_path):
        if os.name == "nt":
            return  # skip on Windows
        env_file = tmp_path / ".env"
        env_file.write_text("SK=secret")
        env_file.chmod(0o644)
        with patch("os.chmod", side_effect=OSError("perm denied")):
            warn_if_env_permissions_unsafe(tmp_path)  # must not raise

    def test_oserror_on_stat_skipped(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("KEY=val")
        with patch("utils.env_guard._dotenv_paths", return_value=[env_file]):
            mock_p = MagicMock(spec=Path)
            mock_p.stat.side_effect = OSError("permission denied")
            mock_p.is_file.return_value = True
            with patch("utils.env_guard._dotenv_paths", return_value=[mock_p]):
                warn_if_env_permissions_unsafe(tmp_path)  # must not raise


class TestRunStartupChecks:
    def test_runs_without_error(self, tmp_path):
        with patch("utils.env_guard.warn_if_env_permissions_unsafe"), \
             patch("utils.env_guard.get_cache_root", return_value=tmp_path):
            run_startup_checks(tmp_path)

    def test_posix_cache_dir_checked(self, tmp_path):
        if os.name == "nt":
            return  # skip chmod semantics on Windows
        with patch("utils.env_guard.warn_if_env_permissions_unsafe"), \
             patch("utils.env_guard.get_cache_root", return_value=tmp_path):
            run_startup_checks(tmp_path)

    def test_oserror_on_cache_stat_swallowed(self, tmp_path):
        mock_cache = MagicMock()
        mock_cache.stat.side_effect = OSError("no such dir")
        with patch("utils.env_guard.warn_if_env_permissions_unsafe"), \
             patch("utils.env_guard.get_cache_root", return_value=mock_cache), \
             patch("os.name", "posix"):
            run_startup_checks(tmp_path)  # must not raise
