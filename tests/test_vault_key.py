"""Tests for core/storage/knowledge/vault_key.py — vault key loading."""
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from core.storage.knowledge.vault_key import _normalize_key, _secure_chmod, load_or_create_vault_key


class TestNormalizeKey:
    def test_strips_whitespace(self):
        assert _normalize_key("  abc  ") == "abc"

    def test_none_like_empty(self):
        assert _normalize_key("") == ""

    def test_normal(self):
        assert _normalize_key("mykey") == "mykey"


class TestLoadOrCreateVaultKey:
    def test_returns_env_key_if_set(self, tmp_path):
        with patch.dict(os.environ, {"AI_TEAM_VAULT_KEY": "env-key-value"}):
            result = load_or_create_vault_key(tmp_path)
        assert result == "env-key-value"

    def test_reads_existing_key_file(self, tmp_path):
        key_file = tmp_path / "vault.key"
        key_file.write_text("saved-key-abc", encoding="ascii")
        env = {k: v for k, v in os.environ.items() if k != "AI_TEAM_VAULT_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = load_or_create_vault_key(tmp_path)
        assert result == "saved-key-abc"

    def test_generates_new_key_with_cryptography(self, tmp_path):
        env = {k: v for k, v in os.environ.items() if k != "AI_TEAM_VAULT_KEY"}
        with patch.dict(os.environ, env, clear=True):
            result = load_or_create_vault_key(tmp_path)
        # cryptography might or might not be installed
        if result is not None:
            assert len(result) > 10
            assert (tmp_path / "vault.key").is_file()

    def test_returns_none_if_no_cryptography(self, tmp_path):
        env = {k: v for k, v in os.environ.items() if k != "AI_TEAM_VAULT_KEY"}
        with patch.dict(os.environ, env, clear=True), \
             patch.dict(__import__("sys").modules, {"cryptography": None, "cryptography.fernet": None}):
            result = load_or_create_vault_key(tmp_path)
        assert result is None

    def test_oserror_on_key_file_read(self, tmp_path):
        key_file = tmp_path / "vault.key"
        key_file.write_text("key", encoding="ascii")
        env = {k: v for k, v in os.environ.items() if k != "AI_TEAM_VAULT_KEY"}
        with patch.dict(os.environ, env, clear=True), \
             patch("pathlib.Path.read_text", side_effect=OSError("perm denied")):
            # Should not raise — fallback to generating new key
            load_or_create_vault_key(tmp_path)


class TestSecureChmod:
    def test_does_not_raise_on_oserror(self, tmp_path):
        p = tmp_path / "file.key"
        p.write_text("x")
        with patch("os.chmod", side_effect=OSError("not allowed")):
            _secure_chmod(p)  # must not raise
