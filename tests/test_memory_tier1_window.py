from __future__ import annotations

from core.storage._token_window import build_token_aware_window, estimate_tokens
from core.storage.memory_coordinator import MemoryCoordinator


def test_token_window_stays_under_budget():
    messages = [{"role": "user", "content": "x " * 1000} for _ in range(20)]
    summaries = [{"body": "summary " * 100}]
    window = build_token_aware_window(messages, summaries, budget=1200, system_prompt_tokens=100)
    total = sum(estimate_tokens(item["content"]) for item in window) + 100
    assert total <= 1200
    assert window


def test_summary_cards_precede_raw_tail():
    messages = [{"role": "user", "content": "recent fact"}]
    summaries = [{"body": "old decision"}]
    window = build_token_aware_window(messages, summaries, budget=5000)
    assert window[0]["role"] == "system"
    assert "old decision" in window[0]["content"]
    assert window[-1]["content"] == "recent fact"


def test_memory_coordinator_prepends_retrieved_memory(monkeypatch):
    class Store:
        def list_summaries(self, convo_id):
            return []

    calls = {}

    def fake_retrieve(query, k=8, rerank="auto", role_key="", importance="normal"):
        calls.update({"query": query, "rerank": rerank, "role_key": role_key, "importance": importance})
        return [{"path": "summary:1", "snip": "sqlite WAL lock fix", "rerank_score": 0.91}]

    monkeypatch.setattr("core.storage.graphrag_store.retrieve_hybrid", fake_retrieve)
    window = MemoryCoordinator(store=Store()).build_context_window(
        "convo",
        messages=[{"role": "user", "content": "latest"}],
        query="database is locked",
        role_key="LEADER_MEDIUM",
        importance="important",
    )

    assert window[0]["role"] == "system"
    assert "[retrieved memory]" in window[0]["content"]
    assert "sqlite WAL lock fix" in window[0]["content"]
    assert calls == {"query": "database is locked", "rerank": "auto", "role_key": "LEADER_MEDIUM", "importance": "important"}
