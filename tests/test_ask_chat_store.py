"""Tests for core/storage/ask_chat_store.py — SQLite CRUD operations."""
import pytest
from pathlib import Path

from core.storage.ask_chat_store import AskChatSQLiteAPI


@pytest.fixture
def store(tmp_path):
    return AskChatSQLiteAPI(data_dir=tmp_path)


class TestListConversations:
    def test_empty_initially(self, store):
        assert store.list_conversations() == []

    def test_lists_after_create(self, store):
        store.create_conversation("chat-1", mode="standard")
        result = store.list_conversations()
        assert len(result) == 1
        assert result[0]["name"] == "chat-1"

    def test_multiple_conversations(self, store):
        store.create_conversation("alpha")
        store.create_conversation("beta")
        names = [r["name"] for r in store.list_conversations()]
        assert "alpha" in names and "beta" in names


class TestGetConversation:
    def test_returns_none_for_missing(self, store):
        assert store.get_conversation("nonexistent") is None

    def test_returns_conversation(self, store):
        store.create_conversation("test-chat", mode="thinking")
        result = store.get_conversation("test-chat")
        assert result is not None
        assert result["name"] == "test-chat"
        assert result["mode"] == "thinking"

    def test_conversation_has_messages_key(self, store):
        store.create_conversation("test")
        result = store.get_conversation("test")
        assert "messages" in result


class TestCreateConversation:
    def test_creates_with_default_mode(self, store):
        store.create_conversation("my-chat")
        conv = store.get_conversation("my-chat")
        assert conv["mode"] == "standard"

    def test_creates_with_custom_mode(self, store):
        store.create_conversation("thinking-chat", mode="thinking")
        conv = store.get_conversation("thinking-chat")
        assert conv["mode"] == "thinking"

    def test_duplicate_name_does_not_raise(self, store):
        store.create_conversation("dup")
        store.create_conversation("dup")  # should be idempotent
        convs = store.list_conversations()
        assert len(convs) == 1


class TestAddMessage:
    def test_adds_message(self, store):
        store.create_conversation("chat")
        store.append_message("chat", role="user", content="hello")
        conv = store.get_conversation("chat")
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "hello"

    def test_multiple_messages_ordered(self, store):
        store.create_conversation("chat")
        store.append_message("chat", role="user", content="first")
        store.append_message("chat", role="assistant", content="second")
        conv = store.get_conversation("chat")
        assert conv["messages"][0]["content"] == "first"
        assert conv["messages"][1]["content"] == "second"

    def test_append_message_updates_conversation_timestamp(self, store):
        store.create_conversation("chat")
        before = store.get_conversation("chat")["updated_at"]
        import time; time.sleep(0.01)
        store.append_message("chat", role="user", content="hi")
        after = store.get_conversation("chat")["updated_at"]
        assert after >= before


class TestDeleteConversation:
    def test_delete_removes_conversation(self, store):
        store.create_conversation("to-delete")
        store.delete_conversation("to-delete")
        assert store.get_conversation("to-delete") is None

    def test_delete_missing_does_not_raise(self, store):
        store.delete_conversation("nonexistent")  # must not raise

    def test_delete_cascades_messages(self, store):
        store.create_conversation("chat")
        store.append_message("chat", role="user", content="msg")
        store.delete_conversation("chat")
        assert store.list_conversations() == []


class TestRenameConversation:
    def test_rename(self, store):
        store.create_conversation("old-name")
        store.rename_conversation("old-name", "new-name")
        assert store.get_conversation("old-name") is None
        assert store.get_conversation("new-name") is not None

    def test_rename_missing_does_not_raise(self, store):
        store.rename_conversation("nonexistent", "new-name")


class TestMessageCount:
    def test_message_count_in_list(self, store):
        store.create_conversation("chat")
        store.append_message("chat", role="user", content="a")
        store.append_message("chat", role="assistant", content="b")
        convs = store.list_conversations()
        assert convs[0]["message_count"] == 2


class TestGetActiveConversation:
    def test_none_when_no_active(self, store):
        assert store.get_active_conversation() is None

    def test_returns_active_after_create(self, store):
        store.create_conversation("active-chat")
        result = store.get_active_conversation()
        assert result is not None
        assert result["name"] == "active-chat"


class TestSetActiveConversation:
    def test_returns_false_for_missing(self, store):
        assert store.set_active_conversation("missing") is False

    def test_returns_true_for_existing(self, store):
        store.create_conversation("my-chat")
        assert store.set_active_conversation("my-chat") is True
        active = store.get_active_conversation()
        assert active["name"] == "my-chat"


class TestDeleteAllConversations:
    def test_clears_all(self, store):
        store.create_conversation("a")
        store.create_conversation("b")
        store.delete_all_conversations()
        assert store.list_conversations() == []

    def test_clears_active_state(self, store):
        store.create_conversation("chat")
        store.delete_all_conversations()
        assert store.get_active_conversation() is None


class TestSetMode:
    def test_sets_mode(self, store):
        store.create_conversation("chat", mode="standard")
        result = store.set_mode("chat", "thinking")
        assert result is True
        conv = store.get_conversation("chat")
        assert conv["mode"] == "thinking"

    def test_returns_false_for_missing(self, store):
        assert store.set_mode("nonexistent", "thinking") is False


class TestAppendMessageEdgeCases:
    def test_returns_false_for_missing_conversation(self, store):
        result = store.append_message("missing-chat", role="user", content="hi")
        assert result is False


class TestRenameConversationEdgeCases:
    def test_returns_false_when_new_name_exists(self, store):
        store.create_conversation("alpha")
        store.create_conversation("beta")
        result = store.rename_conversation("alpha", "beta")
        assert result is False

    def test_updates_active_conversation_name(self, store):
        store.create_conversation("old-active")
        store.set_active_conversation("old-active")
        store.rename_conversation("old-active", "new-active")
        active = store.get_active_conversation()
        assert active is not None
        assert active["name"] == "new-active"


class TestMigrateLegacyJson:
    def test_missing_file_returns_false(self, store, tmp_path):
        result = store.migrate_legacy_json(tmp_path / "missing.json")
        assert result is False

    def test_skips_when_data_exists(self, store, tmp_path):
        store.create_conversation("existing")
        json_file = tmp_path / "legacy.json"
        json_file.write_text('{"chats": {"new-chat": {}}, "active_chat": ""}', encoding="utf-8")
        result = store.migrate_legacy_json(json_file)
        assert result is False

    def test_migrates_valid_data(self, store, tmp_path):
        data = {
            "chats": {
                "migrated-chat": {
                    "mode": "standard",
                    "messages": [{"role": "user", "content": "hello", "model": "", "token_limit": 0}],
                }
            },
            "active_chat": "migrated-chat",
        }
        import json
        json_file = tmp_path / "legacy.json"
        json_file.write_text(json.dumps(data), encoding="utf-8")
        result = store.migrate_legacy_json(json_file)
        assert result is True
        conv = store.get_conversation("migrated-chat")
        assert conv is not None
        assert len(conv["messages"]) == 1
        # Backup created
        assert (tmp_path / "legacy.migrated.backup.json").exists()

    def test_invalid_json_returns_false(self, store, tmp_path):
        json_file = tmp_path / "bad.json"
        json_file.write_text("not json at all {{{", encoding="utf-8")
        result = store.migrate_legacy_json(json_file)
        assert result is False

    def test_non_dict_json_returns_false(self, store, tmp_path):
        import json
        json_file = tmp_path / "list.json"
        json_file.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
        result = store.migrate_legacy_json(json_file)
        assert result is False


class TestClearAskChatStoreCache:
    def test_clears_cache(self, tmp_path):
        from core.storage.ask_chat_store import get_ask_chat_store, clear_ask_chat_store_cache
        s1 = get_ask_chat_store(tmp_path)
        clear_ask_chat_store_cache()
        s2 = get_ask_chat_store(tmp_path)
        # After clear, a new instance is created (different object)
        assert s1 is not s2

    def test_singleton_before_clear(self, tmp_path):
        from core.storage.ask_chat_store import get_ask_chat_store, clear_ask_chat_store_cache
        clear_ask_chat_store_cache()
        s1 = get_ask_chat_store(tmp_path)
        s2 = get_ask_chat_store(tmp_path)
        assert s1 is s2
        clear_ask_chat_store_cache()
