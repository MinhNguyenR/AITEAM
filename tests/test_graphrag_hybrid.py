from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import core.storage.graphrag_store as gs
from core.storage.rerank_client import RerankResult


def test_retrieve_hybrid_uses_vector_when_available(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    db = tmp_path / "graphrag.sqlite"
    fake_client = MagicMock()
    fake_client.embeddings.create.side_effect = [
        SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 0.0])]),
        SimpleNamespace(data=[SimpleNamespace(embedding=[0.0, 1.0])]),
        SimpleNamespace(data=[SimpleNamespace(embedding=[0.0, 1.0])]),
    ]
    with patch("core.storage.graphrag_store._db_path", return_value=db), patch("openai.OpenAI", return_value=fake_client):
        gs.upsert_context_snapshot("task", "alpha backend", kind="context", path="doc-alpha")
        gs.upsert_context_snapshot("task", "beta frontend", kind="context", path="doc-beta")
        hits = gs.retrieve_hybrid("semantic beta", k=2, importance="important")

    assert hits
    assert hits[0]["path"].endswith("doc-beta") or hits[0].get("doc_id", "").endswith("doc-beta")


def test_retrieve_hybrid_falls_back_to_fts(tmp_path):
    db = tmp_path / "graphrag.sqlite"
    with patch("core.storage.graphrag_store._db_path", return_value=db), patch("core.storage.graphrag_store._vector_rows", return_value=[]):
        gs.upsert_context_snapshot("task", "python sqlite memory", kind="context", path="doc", embed=False)
        hits = gs.retrieve_hybrid("python sqlite", k=1)

    assert len(hits) == 1
    assert hits[0]["path"].endswith("doc")


def test_retrieve_hybrid_reranks_candidates_when_requested(tmp_path):
    rows = [
        {"task_uuid": "task", "kind": "context", "path": f"doc-{idx}", "producer": "test", "snip": f"snippet {idx}"}
        for idx in range(8)
    ]

    class FakeReranker:
        model = "cohere/rerank-4-pro"

        def __init__(self, *, db_path=None):
            self.db_path = db_path

        def rerank(self, query, documents, *, top_n=12):
            assert query == "important sqlite locking implementation details"
            assert len(documents) == 8
            return [RerankResult(index=7, relevance_score=0.99), RerankResult(index=2, relevance_score=0.75)]

    with patch("core.storage.graphrag_store._db_path", return_value=tmp_path / "graphrag.sqlite"), patch(
        "core.storage.graphrag_store.search_fts", return_value=rows
    ), patch("core.storage.graphrag_store._vector_rows", return_value=[]), patch("core.storage.rerank_client.RerankClient", FakeReranker):
        hits = gs.retrieve_hybrid(
            "important sqlite locking implementation details",
            k=3,
            rerank="always",
            candidate_limit=30,
            top_n=3,
        )

    assert [hit["path"] for hit in hits[:2]] == ["doc-7", "doc-2"]
    assert hits[0]["rerank_score"] == 0.99
    assert hits[0]["retrieval_stage"] == "hybrid_reranked"


def test_retrieve_hybrid_rerank_failure_keeps_hybrid_order(tmp_path):
    rows = [
        {"task_uuid": "task", "kind": "context", "path": f"doc-{idx}", "producer": "test", "snip": f"snippet {idx}"}
        for idx in range(8)
    ]

    class FailingReranker:
        model = "cohere/rerank-4-pro"

        def __init__(self, *, db_path=None):
            self.db_path = db_path

        def rerank(self, query, documents, *, top_n=12):
            raise RuntimeError("rerank unavailable")

    with patch("core.storage.graphrag_store._db_path", return_value=tmp_path / "graphrag.sqlite"), patch(
        "core.storage.graphrag_store.search_fts", return_value=rows
    ), patch("core.storage.graphrag_store._vector_rows", return_value=[]), patch("core.storage.rerank_client.RerankClient", FailingReranker):
        hits = gs.retrieve_hybrid("important sqlite locking implementation details", k=3, rerank="always")

    assert [hit["path"] for hit in hits] == ["doc-0", "doc-1", "doc-2"]
