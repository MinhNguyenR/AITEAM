from __future__ import annotations

import sqlite3

import pytest

from core.storage.knowledge import SqliteKnowledgeRepository


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_TEAM_VAULT_KEY", raising=False)
    r = SqliteKnowledgeRepository(base_dir=tmp_path)
    yield r


def test_store_then_retrieve_and_search(repo):
    cid = repo.store("Alpha note", "python sqlite knowledge base rocks", tags=["py"])
    got = repo.retrieve(cid)
    assert got is not None
    assert got["title"] == "Alpha note"
    assert "python" in got["content"]

    hits = repo.smart_search("sqlite knowledge")
    assert any(h["id"] == cid for h in hits)


def test_store_batch_single_transaction(repo):
    items = [
        ("T1", "alpha beta gamma", ["t1"]),
        ("T2", "delta epsilon zeta", ["t2"]),
        ("T3", "eta theta iota", ["t3"]),
    ]
    ids = repo.store_batch(items)
    assert len(ids) == 3
    assert repo.count() == 3
    hits = repo.smart_search("epsilon")
    assert any(h["title"] == "T2" for h in hits)


def test_wal_and_indexes_enabled(repo):
    with sqlite3.connect(repo.index_db) as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert str(mode).lower() == "wal"
        idx_rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='knowledge_index'"
        ).fetchall()
        names = {r[0] for r in idx_rows}
        assert "idx_updated_at" in names
        assert "idx_tags" in names


def test_delete_removes_vault_file(repo, tmp_path):
    cid = repo.store("X", "some payload", tags=["x"])
    vault_file = tmp_path / "vault" / f"{cid}.zbin"
    assert vault_file.exists()
    assert repo.delete(cid) is True
    assert not vault_file.exists()
    assert repo.retrieve(cid) is None
