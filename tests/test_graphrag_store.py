"""Tests for core/storage/graphrag_store.py — SQLite FTS5 + edge store."""
from pathlib import Path
from unittest.mock import patch

import pytest

import core.storage.graphrag_store as gs


def _make_db(tmp_path):
    """Return a tmp db path and patch _db_path to use it."""
    db = tmp_path / "graphrag.sqlite"
    return db


class TestEnsureSchema:
    def test_creates_tables(self, tmp_path):
        import sqlite3
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            conn = gs._connect()
            gs._ensure_schema(conn)
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        assert "rag_edges" in tables
        conn.close()


class TestDeleteByContextPath:
    def test_no_error_when_file_not_in_db(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.delete_by_context_path("/some/path/context.md")  # must not raise

    def test_deletes_matching_rows(self, tmp_path):
        import sqlite3
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            # First upsert something, then delete it
            gs.upsert_context_snapshot("uuid1", "hello world", kind="context",
                                       path=str(tmp_path / "ctx.md"))
            gs.delete_by_context_path(str(tmp_path / "ctx.md"))
            # Verify it's gone
            conn = gs._connect()
            gs._ensure_schema(conn)
            count = conn.execute("SELECT COUNT(*) FROM rag_edges").fetchone()[0]
            conn.close()
        assert count == 0


class TestUpsertContextSnapshot:
    def test_basic_upsert(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.upsert_context_snapshot("uuid-1", "Some context text", kind="context",
                                       path="/path/to/ctx.md")
            conn = gs._connect()
            gs._ensure_schema(conn)
            edges = conn.execute("SELECT * FROM rag_edges").fetchall()
            conn.close()
        assert len(edges) == 1

    def test_no_task_uuid_no_edge(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.upsert_context_snapshot("", "text", kind="context", path="/path/ctx.md")
            conn = gs._connect()
            gs._ensure_schema(conn)
            edges = conn.execute("SELECT COUNT(*) FROM rag_edges").fetchone()[0]
            conn.close()
        assert edges == 0

    def test_long_text_truncated(self, tmp_path):
        db = _make_db(tmp_path)
        long_text = "x" * 600_000
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.upsert_context_snapshot("uuid-2", long_text, kind="context", path="/path.md")
            # must not raise


class TestSearchFts:
    def test_empty_query_returns_empty(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            result = gs.search_fts("")
        assert result == []

    def test_single_char_query_returns_empty(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            result = gs.search_fts("a")
        assert result == []

    def test_no_match_returns_empty(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            result = gs.search_fts("zzzmatch_nothing_xyz")
        assert result == []


class TestTryIngestContextMd:
    def test_missing_file_is_noop(self, tmp_path):
        ctx = tmp_path / "missing.md"
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.try_ingest_context_md(ctx, {}, "leader")  # must not raise

    def test_no_context_marker_skipped(self, tmp_path):
        ctx = tmp_path / "context.md"
        ctx.write_text("# NO_CONTEXT\nThis is intentionally empty.")
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.try_ingest_context_md(ctx, {"task_uuid": "uuid-1"}, "leader")
            conn = gs._connect()
            gs._ensure_schema(conn)
            count = conn.execute("SELECT COUNT(*) FROM rag_edges").fetchone()[0]
            conn.close()
        assert count == 0

    def test_valid_file_ingested(self, tmp_path):
        ctx = tmp_path / "context.md"
        ctx.write_text("# My Plan\n\nSome context content here.")
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.try_ingest_context_md(ctx, {"task_uuid": "uuid-2"}, "leader")
            conn = gs._connect()
            gs._ensure_schema(conn)
            count = conn.execute("SELECT COUNT(*) FROM rag_edges").fetchone()[0]
            conn.close()
        assert count >= 1


class TestNeighborEdges:
    def test_returns_empty_when_no_edges(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            result = gs.neighbor_edges("no-such-node")
        assert result == []

    def test_returns_edges_for_node(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            gs.upsert_context_snapshot("uuid-3", "content", kind="context", path="/path3.md")
            result = gs.neighbor_edges("uuid-3")
        assert len(result) >= 1


class TestIngestWorkspace:
    def test_is_noop(self):
        gs.ingest_workspace("anything", key="value")  # must not raise


class TestSearchGraph:
    def test_delegates_to_search_fts(self, tmp_path):
        db = _make_db(tmp_path)
        with patch("core.storage.graphrag_store._db_path", return_value=db):
            result = gs.search_graph("python code")
        assert isinstance(result, list)
