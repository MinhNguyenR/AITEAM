from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

import core.storage.graphrag_store as gs
from core.storage.embedding_client import EmbeddingClient
from core.storage.memory_cost_guard import get_memory_cost_guard
from core.storage.memory_settler import MemorySettler


def test_memory_guard_blocks_when_mode_off(monkeypatch):
    monkeypatch.setenv("AI_TEAM_MEMORY_API_MODE", "off")
    decision = get_memory_cost_guard().check("embedding", role_key="MEMORY_EMBEDDING", model="m", input_tokens=10)
    assert decision.allowed is False
    assert "off" in decision.reason


def test_embedding_client_respects_guard_off(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_TEAM_MEMORY_API_MODE", "off")
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    fake_client = MagicMock()
    with patch("openai.OpenAI", return_value=fake_client):
        with pytest.raises(RuntimeError, match="blocked"):
            EmbeddingClient(db_path=tmp_path / "graphrag.sqlite").embed("paid call")
    fake_client.embeddings.create.assert_not_called()


def test_workflow_step_ingest_does_not_embed_by_default(tmp_path):
    with patch("core.storage.graphrag_store._db_path", return_value=tmp_path / "graphrag.sqlite"), patch(
        "core.storage.graphrag_store._try_embed_doc"
    ) as embed:
        gs.upsert_context_snapshot("thread", "node payload", kind="workflow_step", path="workflow:thread:Leader")
    embed.assert_not_called()


def test_prompt_doc_does_not_embed_without_opt_in(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_TEAM_EMBED_PROMPT_DOCS", raising=False)
    with patch("core.storage.graphrag_store._db_path", return_value=tmp_path / "graphrag.sqlite"), patch(
        "core.storage.graphrag_store._try_embed_doc"
    ) as embed:
        gs.ingest_prompt_doc("task", "Leader", "plan", "prompt", "response")
    embed.assert_not_called()


def test_same_doc_body_hash_does_not_reembed(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    db = tmp_path / "graphrag.sqlite"

    def fake_embed(doc_id, body, *, body_hash=""):
        conn = gs._connect()
        gs._ensure_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO doc_embeddings(doc_id, embedding, dim, model, body_hash, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (doc_id, b"1234", 1, "test-embedding", body_hash, "test"),
        )
        conn.commit()
        conn.close()

    with patch("core.storage.graphrag_store._db_path", return_value=db), patch(
        "core.storage.graphrag_store._try_embed_doc", side_effect=fake_embed
    ) as embed:
        gs.upsert_context_snapshot("task", "same durable memory", kind="conversation_summary", path="summary:1")
        gs.upsert_context_snapshot("task", "same durable memory", kind="conversation_summary", path="summary:1")
    assert embed.call_count == 1


def test_settler_flush_all_does_not_model_compact_by_default(monkeypatch):
    monkeypatch.delenv("AI_TEAM_SETTLE_ON_EXIT_WITH_MODEL", raising=False)
    settler = MemorySettler(idle_seconds=999)
    settler._last_active["c1"] = 1.0
    with patch.object(settler, "force_settle") as force:
        settler.flush_all()
    force.assert_not_called()


def test_normal_retrieve_does_not_embed_query_for_vector_search(tmp_path):
    rows = [{"task_uuid": "task", "kind": "context", "path": "doc-1", "producer": "test", "snip": "plain memory"}]
    with patch("core.storage.graphrag_store.search_fts", return_value=rows), patch("core.storage.graphrag_store._vector_rows") as vector:
        hits = gs.retrieve_hybrid("hello there", k=1, rerank="off", role_key="CHAT_MODEL_STANDARD", importance="normal")
    vector.assert_not_called()
    assert hits == rows
