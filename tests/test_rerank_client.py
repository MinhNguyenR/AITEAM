from __future__ import annotations

import json
from unittest.mock import patch

from core.config import config
from core.storage.rerank_client import RerankClient


class _Response:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_memory_reranker_registry_is_available() -> None:
    cfg = config.get_worker("MEMORY_RERANKER")
    assert cfg is not None
    assert cfg["model"] == "cohere/rerank-4-pro"
    assert cfg["endpoint"] == "rerank"


def test_rerank_client_calls_openrouter_and_caches(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    calls = {"count": 0}

    def fake_urlopen(request, timeout):
        calls["count"] += 1
        body = json.loads(request.data.decode("utf-8"))
        assert request.full_url.endswith("/rerank")
        assert body["model"] == "cohere/rerank-4-pro"
        assert body["query"] == "sqlite locking"
        assert body["top_n"] == 2
        return _Response(
            {
                "results": [
                    {"index": 1, "relevance_score": 0.98},
                    {"index": 0, "relevance_score": 0.12},
                ]
            }
        )

    with patch("core.storage.rerank_client.urlopen", side_effect=fake_urlopen):
        client = RerankClient(db_path=tmp_path / "graphrag.sqlite")
        first = client.rerank("sqlite locking", ["general sqlite", "database is locked WAL"], top_n=2)
        second = client.rerank("sqlite locking", ["general sqlite", "database is locked WAL"], top_n=2)

    assert [item.index for item in first] == [1, 0]
    assert [item.index for item in second] == [1, 0]
    assert calls["count"] == 1
