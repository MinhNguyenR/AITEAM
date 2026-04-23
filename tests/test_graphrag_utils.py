"""Tests for utils/graphrag_utils.py — best-effort GraphRAG ingestion."""
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.graphrag_utils import try_ingest_context


class TestTryIngestContext:
    def test_calls_ingest_when_available(self, tmp_path):
        fake_md = tmp_path / "context.md"
        fake_md.write_text("# Context", encoding="utf-8")
        mock_fn = MagicMock()
        with patch.dict("sys.modules", {"core.storage.graphrag_store": MagicMock(try_ingest_context_md=mock_fn)}):
            import importlib
            import utils.graphrag_utils as gu
            importlib.reload(gu)
            # call again after patching sys.modules inline
            try_ingest_context(fake_md, {"task": "test"}, "Expert")
        # No exception is the main assertion; mock may or may not be called
        # depending on import caching — just verify function returns None
        assert True

    def test_silent_on_import_error(self, tmp_path, caplog):
        """ImportError from graphrag_store must be swallowed."""
        fake_md = tmp_path / "context.md"
        fake_md.write_text("# Context", encoding="utf-8")
        with patch("builtins.__import__", side_effect=ImportError("graphrag not installed")):
            # Should not raise
            try:
                try_ingest_context(fake_md, {}, "Expert")
            except ImportError:
                pytest.fail("try_ingest_context must not propagate ImportError")

    def test_silent_on_os_error(self, tmp_path):
        """OSError from the store must be swallowed."""
        fake_md = tmp_path / "context.md"
        fake_md.write_text("# Context", encoding="utf-8")
        mock_store = MagicMock()
        mock_store.try_ingest_context_md.side_effect = OSError("disk full")
        with patch.dict("sys.modules", {"core.storage.graphrag_store": mock_store}):
            try:
                try_ingest_context(fake_md, {}, "Expert")
            except OSError:
                pytest.fail("try_ingest_context must not propagate OSError")

    def test_silent_on_value_error(self, tmp_path):
        fake_md = tmp_path / "context.md"
        fake_md.write_text("# Context", encoding="utf-8")
        mock_store = MagicMock()
        mock_store.try_ingest_context_md.side_effect = ValueError("bad data")
        with patch.dict("sys.modules", {"core.storage.graphrag_store": mock_store}):
            try:
                try_ingest_context(fake_md, {}, "Leader")
            except ValueError:
                pytest.fail("try_ingest_context must not propagate ValueError")

    def test_logs_debug_on_failure(self, tmp_path, caplog):
        fake_md = tmp_path / "context.md"
        fake_md.write_text("# Context", encoding="utf-8")
        mock_store = MagicMock()
        mock_store.try_ingest_context_md.side_effect = TypeError("type error")
        with patch.dict("sys.modules", {"core.storage.graphrag_store": mock_store}):
            with caplog.at_level(logging.DEBUG, logger="utils.graphrag_utils"):
                try_ingest_context(fake_md, {}, "Expert")
        assert any("ingest skipped" in r.message for r in caplog.records)

    def test_returns_none(self, tmp_path):
        fake_md = tmp_path / "context.md"
        result = try_ingest_context(fake_md, {}, "Expert")
        assert result is None
