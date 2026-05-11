from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.storage.embedding_client import EmbeddingClient, blob_to_vector, vector_to_blob


def test_memory_embedding_registry_available():
    from core.config.registry import get_worker_config

    cfg = get_worker_config("MEMORY_EMBEDDING")
    assert cfg is not None
    assert cfg["model"] == "perplexity/pplx-embed-v1-0.6b"
    assert cfg["endpoint"] == "embeddings"


def test_embedding_cache_hit_avoids_second_api_call(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    fake_client = MagicMock()
    fake_client.embeddings.create.return_value = SimpleNamespace(
        data=[SimpleNamespace(embedding=[0.1, 0.2, 0.3])]
    )
    with patch("openai.OpenAI", return_value=fake_client):
        client = EmbeddingClient(db_path=tmp_path / "graphrag.sqlite")
        first = client.embed("hello")
        second = client.embed("hello")

    assert first.cached is False
    assert second.cached is True
    assert fake_client.embeddings.create.call_count == 1
    assert blob_to_vector(first.blob) == blob_to_vector(second.blob)


def test_vector_blob_round_trip():
    vector = [1.0, 0.5, -0.25]
    assert blob_to_vector(vector_to_blob(vector)) == vector
