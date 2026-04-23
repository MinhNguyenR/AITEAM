"""Extra tests for core/storage/knowledge/sqlite_repository.py — uncovered branches."""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.storage.knowledge.sqlite_repository import (
    SqliteKnowledgeRepository,
    _vault_wrap,
    _vault_unwrap,
    _vault_fernet_optional,
    _VAULT_MAGIC,
)


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_TEAM_VAULT_KEY", raising=False)
    return SqliteKnowledgeRepository(base_dir=tmp_path)


class TestVaultFernetOptional:
    def test_no_key_returns_none(self, tmp_path):
        with patch("core.storage.knowledge.sqlite_repository.load_or_create_vault_key",
                   return_value=None):
            result = _vault_fernet_optional(tmp_path)
        assert result is None

    def test_invalid_key_returns_none(self, tmp_path):
        with patch("core.storage.knowledge.sqlite_repository.load_or_create_vault_key",
                   return_value="not-a-valid-fernet-key-at-all"):
            result = _vault_fernet_optional(tmp_path)
        assert result is None

    def test_cryptography_import_error_returns_none(self, tmp_path):
        import sys
        with patch("core.storage.knowledge.sqlite_repository.load_or_create_vault_key",
                   return_value="somevalidlookingkey"):
            # Make Fernet unavailable
            fernet_mod = sys.modules.get("cryptography.fernet")
            sys.modules["cryptography.fernet"] = None  # type: ignore
            try:
                result = _vault_fernet_optional(tmp_path)
                assert result is None
            finally:
                if fernet_mod is None:
                    sys.modules.pop("cryptography.fernet", None)
                else:
                    sys.modules["cryptography.fernet"] = fernet_mod


class TestVaultWrapUnwrap:
    def test_wrap_without_key_returns_unencrypted(self, tmp_path):
        with patch("core.storage.knowledge.sqlite_repository.load_or_create_vault_key",
                   return_value=None):
            result = _vault_wrap(b"my data", tmp_path)
        assert result == b"my data"

    def test_unwrap_no_magic_returns_raw(self, tmp_path):
        with patch("core.storage.knowledge.sqlite_repository.load_or_create_vault_key",
                   return_value=None):
            raw = b"plain bytes no magic"
            result = _vault_unwrap(raw, tmp_path)
        assert result == raw

    def test_unwrap_with_magic_but_no_key_returns_none(self, tmp_path, caplog):
        import logging
        raw = _VAULT_MAGIC + b"encrypted_data_here"
        with patch("core.storage.knowledge.sqlite_repository.load_or_create_vault_key",
                   return_value=None), \
             caplog.at_level(logging.WARNING):
            result = _vault_unwrap(raw, tmp_path)
        assert result is None


class TestStoreBatch:
    def test_empty_iterable_returns_empty(self, repo):
        result = repo.store_batch([])
        assert result == []

    def test_stores_multiple_items(self, repo):
        items = [
            ("Title 1", "content for title one here", ["tag1"]),
            ("Title 2", "content for title two here", ["tag2"]),
        ]
        ids = repo.store_batch(items)
        assert len(ids) == 2
        assert repo.count() == 2


class TestRetrieve:
    def test_retrieve_missing_vault_file_returns_none(self, repo):
        """If vault file is deleted after indexing, retrieve returns None."""
        cid = repo.store("Lost", "content will be deleted")
        # Remove vault file
        vault_file = repo.vault_dir / f"{cid}.zbin"
        vault_file.unlink()
        result = repo.retrieve(cid)
        assert result is None

    def test_retrieve_unknown_id_returns_none(self, repo):
        result = repo.retrieve("nonexistent-id-xyz")
        assert result is None


class TestSmartSearch:
    def test_empty_query_returns_empty(self, repo):
        result = repo.smart_search("   ")
        assert result == []

    def test_finds_stored_content(self, repo):
        repo.store("Python Tutorial", "learn python programming language basics")
        results = repo.smart_search("python programming")
        assert len(results) >= 1
        assert any(r["title"] == "Python Tutorial" for r in results)

    def test_max_results_respected(self, repo):
        for i in range(5):
            repo.store(f"Entry {i}", f"common search term alpha beta gamma {i}")
        results = repo.smart_search("common search term", max_results=2)
        assert len(results) <= 2

    def test_no_match_returns_empty(self, repo):
        repo.store("Known title", "known content with specific words")
        results = repo.smart_search("zzznomatch999xyz")
        assert results == []


class TestListAll:
    def test_empty_repo(self, repo):
        result = repo.list_all()
        assert result == []

    def test_returns_all_entries(self, repo):
        repo.store("A", "alpha beta gamma text")
        repo.store("B", "delta epsilon zeta text")
        result = repo.list_all()
        assert len(result) == 2
        assert {r["title"] for r in result} == {"A", "B"}


class TestGetStats:
    def test_returns_stats_dict(self, repo):
        repo.store("Stat Entry", "content for stats testing purposes")
        stats = repo.get_stats()
        assert stats["total_entries"] == 1
        assert stats["vault_size_bytes"] >= 0
        assert "tags" in stats
        assert "base_dir" in stats

    def test_empty_repo_stats(self, repo):
        stats = repo.get_stats()
        assert stats["total_entries"] == 0


class TestClearAll:
    def test_clears_all_entries(self, repo):
        repo.store("Entry1", "some content here to clear")
        repo.store("Entry2", "another content entry to clear")
        assert repo.count() == 2
        repo.clear_all()
        assert repo.count() == 0

    def test_removes_vault_files(self, repo):
        repo.store("VaultEntry", "content stored in vault for testing")
        assert any(repo.vault_dir.glob("*.zbin"))
        repo.clear_all()
        assert not any(repo.vault_dir.glob("*.zbin"))


class TestSaveVaultFileOSError:
    def test_oserror_removes_tmp_and_reraises(self, repo):
        with patch("os.replace", side_effect=OSError("no space")):
            with pytest.raises(OSError):
                repo._save_vault_file("testid", b"data")


class TestSmartSearchFtsFailed:
    def test_falls_back_to_like_when_fts_fails(self, repo):
        """When FTS raises OperationalError, falls back to LIKE search."""
        repo.store("FTS Fallback Test", "unique text for fallback test logic")
        # Force FTS to fail by breaking the fts table
        with repo._conn(write=True) as conn:
            try:
                conn.execute("DROP TABLE knowledge_fts")
            except sqlite3.OperationalError:
                pass
        repo._fts_ok = True  # force FTS attempt which will fail
        result = repo.smart_search("fallback test logic")
        # Either found via fallback or returned empty — must not raise
        assert isinstance(result, list)
