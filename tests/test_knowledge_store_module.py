"""Tests for core/storage/knowledge_store.py — thin module wrappers."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestKnowledgeStoreVaultHelpers:
    def test_vault_wrap_with_config(self):
        import sys
        from core.storage.knowledge_store import _vault_wrap
        mock_impl = MagicMock(return_value=b"wrapped")
        mock_cfg = MagicMock()
        mock_cfg.Config.BASE_DIR = Path("/fake/base")
        with patch("core.storage.knowledge_store._vault_wrap_impl", mock_impl), \
             patch.dict(sys.modules, {"core.config": mock_cfg}):
            result = _vault_wrap(b"data")
        mock_impl.assert_called_once()
        assert result == b"wrapped"

    def test_vault_wrap_import_error_uses_home(self):
        import sys
        from core.storage.knowledge_store import _vault_wrap
        mock_impl = MagicMock(return_value=b"wrapped_fallback")
        with patch("core.storage.knowledge_store._vault_wrap_impl", mock_impl), \
             patch.dict(sys.modules, {"core.config": None}):
            result = _vault_wrap(b"payload")
        assert result == b"wrapped_fallback"
        call_args = mock_impl.call_args
        assert ".ai-team" in str(call_args[0][1])

    def test_vault_unwrap_with_config(self):
        import sys
        from core.storage.knowledge_store import _vault_unwrap
        mock_impl = MagicMock(return_value=b"unwrapped")
        mock_cfg = MagicMock()
        mock_cfg.Config.BASE_DIR = Path("/fake/base")
        with patch("core.storage.knowledge_store._vault_unwrap_impl", mock_impl), \
             patch.dict(sys.modules, {"core.config": mock_cfg}):
            result = _vault_unwrap(b"raw")
        assert result == b"unwrapped"

    def test_vault_unwrap_import_error_uses_home(self):
        import sys
        from core.storage.knowledge_store import _vault_unwrap
        mock_impl = MagicMock(return_value=None)
        with patch("core.storage.knowledge_store._vault_unwrap_impl", mock_impl), \
             patch.dict(sys.modules, {"core.config": None}):
            result = _vault_unwrap(b"data")
        mock_impl.assert_called_once()


class TestGetBrain:
    def test_returns_singleton(self, tmp_path):
        import core.storage.knowledge_store as ks
        mock_instance = MagicMock()
        mock_class = MagicMock(return_value=mock_instance)
        # Reset the singleton
        ks._brain_instance = None
        with patch("core.storage.knowledge_store.SqliteKnowledgeRepository", mock_class):
            b1 = ks.get_brain()
            b2 = ks.get_brain()
        assert b1 is b2
        assert mock_class.call_count == 1
        ks._brain_instance = None  # cleanup

    def test_existing_instance_returned(self, tmp_path):
        import core.storage.knowledge_store as ks
        existing = MagicMock()
        ks._brain_instance = existing
        result = ks.get_brain()
        assert result is existing
        ks._brain_instance = None  # cleanup


class TestSmartSearchModule:
    def test_delegates_to_brain(self, tmp_path):
        import core.storage.knowledge_store as ks
        mock_brain = MagicMock()
        mock_brain.smart_search.return_value = [{"id": "r1"}]
        ks._brain_instance = None
        with patch("core.storage.knowledge_store.SqliteKnowledgeRepository", return_value=mock_brain):
            result = ks.smart_search("my query", max_results=2)
        assert result == [{"id": "r1"}]
        mock_brain.smart_search.assert_called_once_with("my query", 2)
        ks._brain_instance = None


class TestStoreKnowledge:
    def test_delegates_to_brain(self, tmp_path):
        import core.storage.knowledge_store as ks
        mock_brain = MagicMock()
        mock_brain.store.return_value = "cid-abc"
        ks._brain_instance = None
        with patch("core.storage.knowledge_store.SqliteKnowledgeRepository", return_value=mock_brain):
            result = ks.store_knowledge("Title", "Content", ["tag1"])
        assert result == "cid-abc"
        mock_brain.store.assert_called_once_with("Title", "Content", ["tag1"])
        ks._brain_instance = None
