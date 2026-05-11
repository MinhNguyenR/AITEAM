from __future__ import annotations

from core.storage.ask_chat_store import AskChatSQLiteAPI
from core.storage.memory_coordinator import MemoryCoordinator
from core.storage.memory_settler import MemorySettler


def test_force_settle_writes_archive(tmp_path, monkeypatch):
    store = AskChatSQLiteAPI(data_dir=tmp_path)
    conv = store.create_conversation("chat")
    store.append_message("chat", "user", "hello memory", token_count=3)
    monkeypatch.setattr("agents.compact_worker.CompactWorker.compact_conversation_range", lambda self, cid, msgs: {"body": "summary", "topics": [], "entities": []})
    coordinator = MemoryCoordinator(store=store, settler=MemorySettler(idle_seconds=999))
    coordinator.force_settle(conv["id"])
    archive = store.get_archive(conv["id"])
    assert archive is not None
    assert "summary" in archive["headline_summary"]


def test_settler_reset_replaces_timer():
    settler = MemorySettler(idle_seconds=999)
    settler.reset("c1")
    first = settler._timers["c1"]
    settler.reset("c1")
    second = settler._timers["c1"]
    assert first is not second
    assert first.is_alive() is False
    second.cancel()
