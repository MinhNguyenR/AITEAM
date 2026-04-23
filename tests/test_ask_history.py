"""Tests for utils/ask_history.py — thin wrappers over AskChatStore."""
import sys
from unittest.mock import MagicMock, patch


def _make_store():
    store = MagicMock()
    store.get_active_conversation.return_value = {"name": "chat1"}
    store.list_conversations.return_value = [
        {"name": "chat1", "message_count": 3},
        {"name": "chat2", "message_count": 1},
    ]
    store.get_conversation.return_value = {"name": "chat1", "mode": "standard"}
    store.create_conversation.return_value = {"name": "new_chat", "mode": "standard"}
    store.set_active_conversation.return_value = True
    store.rename_conversation.return_value = True
    store.delete_conversation.return_value = True
    store.set_mode.return_value = True
    return store


def _import_ask_history(mock_store):
    """Import ask_history with a mocked module-level _store."""
    for mod in ("utils.ask_history", "core.storage.ask_history"):
        if mod in sys.modules:
            del sys.modules[mod]
    with patch("utils.file_manager.ensure_ask_data_dir", return_value=MagicMock()), \
         patch("core.storage.ask_chat_store.get_ask_chat_store", return_value=mock_store):
        import utils.ask_history as ah
    return ah


class TestLoadStore:
    def test_active_chat_populated(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        result = ah.load_store()
        assert result["active_chat"] == "chat1"
        assert "chats" in result

    def test_no_active_chat(self):
        ms = _make_store()
        ms.get_active_conversation.return_value = None
        ah = _import_ask_history(ms)
        result = ah.load_store()
        assert result["active_chat"] == ""


class TestListChats:
    def test_returns_names(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        names = ah.list_chats({})
        assert names == ["chat1", "chat2"]


class TestListChatRecords:
    def test_default_sort(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        records = ah.list_chat_records({})
        assert len(records) == 2

    def test_name_asc_sort(self):
        ms = _make_store()
        ms.list_conversations.return_value = [
            {"name": "zebra"},
            {"name": "apple"},
        ]
        ah = _import_ask_history(ms)
        records = ah.list_chat_records({}, sort_by="name_asc")
        assert records[0]["name"] == "apple"


class TestEnsureChat:
    def test_existing_returns_existing(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        result = ah.ensure_chat({}, "chat1")
        assert result["name"] == "chat1"
        ms.create_conversation.assert_not_called()

    def test_missing_creates(self):
        ms = _make_store()
        ms.get_conversation.return_value = None
        ah = _import_ask_history(ms)
        result = ah.ensure_chat({}, "new_chat")
        ms.create_conversation.assert_called_once()


class TestCreateJoinRenameDelete:
    def test_create_chat(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        ah.create_chat({}, "new")
        ms.create_conversation.assert_called_with("new", mode="standard")

    def test_join_chat(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        result = ah.join_chat({}, "chat1")
        assert result is True

    def test_rename_chat(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        assert ah.rename_chat({}, "old", "new") is True

    def test_delete_chat(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        assert ah.delete_chat({}, "chat1") is True

    def test_delete_chats_bulk(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        count = ah.delete_chats_bulk({}, ["chat1", "chat2"])
        assert count == 2

    def test_delete_all_chats(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        ah.delete_all_chats({})
        ms.delete_all_conversations.assert_called_once()


class TestGetActiveChat:
    def test_returns_active(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        result = ah.get_active_chat({})
        assert result["name"] == "chat1"


class TestAppendMessage:
    def test_delegates_to_store(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        ah.append_message({}, "chat1", "user", "hello", model="gpt-4", token_limit=100)
        ms.append_message.assert_called_with("chat1", "user", "hello", model="gpt-4", token_limit=100)


class TestSetChatMode:
    def test_delegates(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        assert ah.set_chat_mode({}, "chat1", "thinking") is True


class TestSaveStore:
    def test_save_is_noop(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        ah.save_store({"active_chat": "x"})  # must not raise


class TestAskDataDir:
    def test_returns_path(self):
        ms = _make_store()
        ah = _import_ask_history(ms)
        result = ah.ask_data_dir()
        assert result is not None
