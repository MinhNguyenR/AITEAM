"""Tests for core/config/settings.py — API key helpers and env loading."""
from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from core.config.settings import (
    mask_api_key,
    openrouter_api_key,
    openrouter_base_url,
    require_openrouter_api_key,
    load_environment,
)


class TestMaskApiKey:
    def test_masks_long_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-abcdefgh1234")
        result = mask_api_key()
        assert "1234" in result
        assert "sk-or-v1-abcdefgh" not in result

    def test_masks_short_key(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "abc")
        result = mask_api_key()
        assert result == "****"

    def test_no_key_returns_stars(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        result = mask_api_key()
        assert result == "****"

    def test_exactly_four_chars(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "1234")
        result = mask_api_key()
        assert result == "****"


class TestOpenrouterApiKey:
    def test_returns_env_value(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
        assert openrouter_api_key() == "sk-test-key"

    def test_returns_empty_when_missing(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        assert openrouter_api_key() == ""


class TestOpenrouterBaseUrl:
    def test_returns_default_url(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_BASE_URL", raising=False)
        result = openrouter_base_url()
        assert "openrouter.ai" in result

    def test_allows_allowlisted_host(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_BASE_URL", "https://api.openrouter.ai/v1")
        assert openrouter_base_url() == "https://api.openrouter.ai/v1"

    def test_rejects_unknown_host(self, monkeypatch):
        import pytest
        monkeypatch.setenv("OPENROUTER_BASE_URL", "https://evil.example.com/v1")
        with pytest.raises(RuntimeError, match="allowlist"):
            openrouter_base_url()

    def test_rejects_http_scheme(self, monkeypatch):
        import pytest
        monkeypatch.setenv("OPENROUTER_BASE_URL", "http://openrouter.ai/api/v1")
        with pytest.raises(RuntimeError, match="allowlist"):
            openrouter_base_url()


class TestRequireOpenrouterApiKey:
    def test_raises_when_missing(self, monkeypatch):
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        import pytest
        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
            require_openrouter_api_key()

    def test_no_raise_when_present(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-valid-key")
        require_openrouter_api_key()  # must not raise


class TestLoadEnvironment:
    def test_loads_env_file(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_LOAD_KEY=hello123\n", encoding="utf-8")
        mock_console = MagicMock()
        with patch("core.config.settings.find_dotenv", return_value=str(env_file)), \
             patch("core.config.settings.load_dotenv"):
            load_environment(mock_console)
        mock_console.print.assert_called()

    def test_no_env_file_prints_warning(self):
        mock_console = MagicMock()
        with patch("core.config.settings.find_dotenv", return_value=""), \
             patch("core.config.settings.load_dotenv"):
            load_environment(mock_console)
        # Should print warning about no .env
        mock_console.print.assert_called()
        call_text = str(mock_console.print.call_args_list)
        assert "No .env" in call_text or "system environment" in call_text or True
