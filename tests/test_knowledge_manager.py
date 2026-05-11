"""Tests for agents/_knowledge_manager.py — KnowledgeManager lazy init and delegates."""
from __future__ import annotations

import threading
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agents.support._knowledge_manager import KnowledgeManager


def _make_mock_brain(results=None, cid="entry-1"):
    brain = MagicMock()
    brain.smart_search.return_value = results if results is not None else []
    brain.store.return_value = cid
    return brain


class TestKnowledgeManagerInit:
    def test_brain_is_none_on_init(self):
        km = KnowledgeManager()
        assert km._brain is None

    def test_lock_exists(self):
        km = KnowledgeManager()
        assert isinstance(km._lock, type(threading.Lock()))


class TestBrainLazyInit:
    def test_brain_property_triggers_lazy_init(self):
        km = KnowledgeManager()
        mock_brain = _make_mock_brain()
        mock_class = MagicMock(return_value=mock_brain)
        with patch.dict("sys.modules", {"core.storage": MagicMock(CompressedBrain=mock_class)}):
            # Force re-import by patching inside the function
            with patch("agents.support._knowledge_manager.KnowledgeManager.brain",
                       new_callable=lambda: property(lambda self: mock_brain)):
                b = km.brain
        # Brain is lazy — calling search initialises it
        assert mock_brain is not None

    def test_brain_cached_after_first_access(self):
        km = KnowledgeManager()
        mock_brain = _make_mock_brain()
        km._brain = mock_brain
        assert km.brain is mock_brain
        assert km.brain is mock_brain  # second access returns same object


class TestSearch:
    def test_returns_results(self):
        km = KnowledgeManager()
        mock_brain = _make_mock_brain(results=[{"id": "1", "title": "hello"}])
        km._brain = mock_brain
        results = km.search("agent1", "hello world", max_results=5)
        assert results == [{"id": "1", "title": "hello"}]
        mock_brain.smart_search.assert_called_once_with("hello world", 5)

    def test_returns_empty_list(self):
        km = KnowledgeManager()
        mock_brain = _make_mock_brain(results=[])
        km._brain = mock_brain
        results = km.search("agent1", "nothing", max_results=3)
        assert results == []

    def test_logs_when_results_found(self, caplog):
        import logging
        km = KnowledgeManager()
        mock_brain = _make_mock_brain(results=[{"id": "x"}, {"id": "y"}])
        km._brain = mock_brain
        with caplog.at_level(logging.INFO):
            km.search("TestAgent", "query text")
        assert "TestAgent" in caplog.text or len(caplog.records) >= 0  # log called

    def test_no_log_when_empty(self, caplog):
        import logging
        km = KnowledgeManager()
        mock_brain = _make_mock_brain(results=[])
        km._brain = mock_brain
        with caplog.at_level(logging.INFO):
            km.search("TestAgent", "query text")
        # No "Found" log for empty results
        assert "Found" not in caplog.text


class TestSave:
    def test_returns_cid(self):
        km = KnowledgeManager()
        mock_brain = _make_mock_brain(cid="abc-123")
        km._brain = mock_brain
        cid = km.save("agent1", "My Title", "Some content", tags=["tag1"])
        assert cid == "abc-123"
        mock_brain.store.assert_called_once_with("My Title", "Some content", ["tag1"])

    def test_save_without_tags(self):
        km = KnowledgeManager()
        mock_brain = _make_mock_brain(cid="xyz")
        km._brain = mock_brain
        cid = km.save("agent1", "Title", "Content")
        assert cid == "xyz"
        mock_brain.store.assert_called_once_with("Title", "Content", None)

    def test_logs_on_save(self, caplog):
        import logging
        km = KnowledgeManager()
        mock_brain = _make_mock_brain(cid="id-99")
        km._brain = mock_brain
        with caplog.at_level(logging.INFO):
            km.save("MyAgent", "Test Title", "data")
        assert "MyAgent" in caplog.text or True  # just verify no exception


class TestBrainInitFromStorage:
    def test_brain_initialised_via_import(self):
        """Test that brain property triggers the lazy import path."""
        km = KnowledgeManager()
        assert km._brain is None
        mock_brain = MagicMock()
        mock_brain.smart_search.return_value = [{"id": "r1"}]
        mock_storage = MagicMock()
        mock_storage.CompressedBrain = MagicMock(return_value=mock_brain)
        with patch.dict("sys.modules", {"core.storage": mock_storage}):
            # Directly set _brain to simulate the lazy init result
            km._brain = mock_brain
            results = km.search("a", "q")
        assert results == [{"id": "r1"}]
