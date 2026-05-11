from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config.constants import AI_TEAM_HOME
from core.storage.ask_chat_store import get_ask_chat_store
from utils.file_manager import ensure_ask_data_dir

_ASK_DATA_DIR = ensure_ask_data_dir()
_LEGACY_JSON = AI_TEAM_HOME / "ask_chats.json"
_LEGACY_DB = AI_TEAM_HOME / "ask-data" / "ask_history.db"
_NEW_DB = _ASK_DATA_DIR / "ask_history.db"
if _LEGACY_DB.is_file() and not _NEW_DB.exists():
    _ASK_DATA_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(_LEGACY_DB, _NEW_DB)
_store = get_ask_chat_store(_ASK_DATA_DIR)
_store.migrate_legacy_json(_LEGACY_JSON)


def load_store() -> Dict[str, Any]:
    active = _store.get_active_conversation()
    active_name = active["name"] if active else ""
    return {"active_chat": active_name, "chats": {}}


def save_store(store: Dict[str, Any]) -> None:
    _ = store


def list_chats(store: Dict[str, Any]) -> List[str]:
    _ = store
    return [r["name"] for r in _store.list_conversations()]


def list_chat_records(store: Dict[str, Any], sort_by: str = "updated_desc") -> List[Dict[str, Any]]:
    _ = store
    records = _store.list_conversations()
    if sort_by == "name_asc":
        records.sort(key=lambda x: x.get("name", "").lower())
    return records


def ensure_chat(store: Dict[str, Any], name: str, mode: str = "standard") -> Dict[str, Any]:
    _ = store
    existing = _store.get_conversation(name)
    if existing:
        return existing
    return _store.create_conversation(name, mode=mode)


def create_chat(store: Dict[str, Any], name: str, mode: str = "standard") -> None:
    _ = store
    _store.create_conversation(name, mode=mode)


def join_chat(store: Dict[str, Any], name: str) -> bool:
    _ = store
    return _store.set_active_conversation(name)


def rename_chat(store: Dict[str, Any], old_name: str, new_name: str) -> bool:
    _ = store
    return _store.rename_conversation(old_name, new_name)


def delete_chat(store: Dict[str, Any], name: str) -> bool:
    _ = store
    return _store.delete_conversation(name)


def delete_chats_bulk(store: Dict[str, Any], names: List[str]) -> int:
    _ = store
    n = 0
    for name in names:
        if _store.delete_conversation(name):
            n += 1
    return n


def delete_all_chats(store: Dict[str, Any]) -> None:
    _ = store
    _store.delete_all_conversations()


def get_active_chat(store: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    _ = store
    return _store.get_active_conversation()


def append_message(store: Dict[str, Any], chat_name: str, role: str, content: str, model: str = "", token_limit: int = 0) -> None:
    _ = store
    return _store.append_message(chat_name, role, content, model=model, token_limit=token_limit)


def set_chat_mode(store: Dict[str, Any], chat_name: str, mode: str) -> bool:
    _ = store
    return _store.set_mode(chat_name, mode)


def ask_data_dir() -> Path:
    return _ASK_DATA_DIR
