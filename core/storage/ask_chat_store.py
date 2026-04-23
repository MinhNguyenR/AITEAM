from __future__ import annotations

import hashlib
import json
import logging
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

from utils.file_manager import ensure_ask_data_dir


class AskChatSQLiteAPI:
    """SQLite API for ask conversations and messages."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or ensure_ask_data_dir()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / "ask_history.db"
        self._init_db()

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ask_conversations (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                mode TEXT NOT NULL DEFAULT 'standard',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ask_messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT NOT NULL DEFAULT '',
                token_limit INTEGER NOT NULL DEFAULT 0,
                ts TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES ask_conversations(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ask_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ask_conversations_updated ON ask_conversations(updated_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ask_messages_conv_ts ON ask_messages(conversation_id, ts)")
        conn.commit()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        self._ensure_schema(conn)
        return conn

    def _init_db(self) -> None:
        with self._connect():
            pass

    def list_conversations(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT c.id, c.name, c.mode, c.created_at, c.updated_at, COUNT(m.id) AS message_count
                FROM ask_conversations c
                LEFT JOIN ask_messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.updated_at DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def get_conversation(self, name: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, mode, created_at, updated_at FROM ask_conversations WHERE name = ?",
                (name,),
            ).fetchone()
            if not row:
                return None
            conv = dict(row)
            msg_rows = conn.execute(
                """
                SELECT role, content, ts, model, token_limit
                FROM ask_messages
                WHERE conversation_id = ?
                ORDER BY ts ASC
                """,
                (conv["id"],),
            ).fetchall()
            conv["messages"] = [dict(m) for m in msg_rows]
            return conv

    def get_active_conversation(self) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM ask_state WHERE key = 'active_conversation'").fetchone()
        if not row:
            return None
        return self.get_conversation(row["value"])

    def set_active_conversation(self, name: str) -> bool:
        with self._connect() as conn:
            exists = conn.execute("SELECT 1 FROM ask_conversations WHERE name = ?", (name,)).fetchone()
            if not exists:
                return False
            conn.execute(
                """
                INSERT INTO ask_state(key, value) VALUES('active_conversation', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (name,),
            )
            conn.commit()
            return True

    def create_conversation(self, name: str, mode: str = "standard") -> Dict[str, Any]:
        now = datetime.now().isoformat()
        conv_id = hashlib.sha256(f"{name}:{now}".encode("utf-8")).hexdigest()[:16]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO ask_conversations(id, name, mode, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET mode=excluded.mode, updated_at=excluded.updated_at
                """,
                (conv_id, name, mode, now, now),
            )
            conn.execute(
                """
                INSERT INTO ask_state(key, value) VALUES('active_conversation', ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value
                """,
                (name,),
            )
            conn.commit()
        return self.get_conversation(name) or {}

    def rename_conversation(self, old_name: str, new_name: str) -> bool:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            exists_new = conn.execute("SELECT 1 FROM ask_conversations WHERE name = ?", (new_name,)).fetchone()
            if exists_new:
                return False
            cur = conn.execute(
                "UPDATE ask_conversations SET name = ?, updated_at = ? WHERE name = ?",
                (new_name, now, old_name),
            )
            if cur.rowcount == 0:
                return False
            active = conn.execute("SELECT value FROM ask_state WHERE key = 'active_conversation'").fetchone()
            if active and active["value"] == old_name:
                conn.execute(
                    """
                    INSERT INTO ask_state(key, value) VALUES('active_conversation', ?)
                    ON CONFLICT(key) DO UPDATE SET value=excluded.value
                    """,
                    (new_name,),
                )
            conn.commit()
            return True

    def delete_conversation(self, name: str) -> bool:
        with self._connect() as conn:
            cur = conn.execute("DELETE FROM ask_conversations WHERE name = ?", (name,))
            if cur.rowcount == 0:
                return False
            active = conn.execute("SELECT value FROM ask_state WHERE key = 'active_conversation'").fetchone()
            if active and active["value"] == name:
                conn.execute("DELETE FROM ask_state WHERE key = 'active_conversation'")
            conn.commit()
            return True

    def delete_all_conversations(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM ask_messages")
            conn.execute("DELETE FROM ask_conversations")
            conn.execute("DELETE FROM ask_state WHERE key = 'active_conversation'")
            conn.commit()

    def set_mode(self, name: str, mode: str) -> bool:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                "UPDATE ask_conversations SET mode = ?, updated_at = ? WHERE name = ?",
                (mode, now, name),
            )
            conn.commit()
            return cur.rowcount > 0

    def append_message(self, name: str, role: str, content: str, model: str = "", token_limit: int = 0) -> bool:
        now = datetime.now().isoformat()
        msg_id = hashlib.sha256(f"{name}:{role}:{now}:{len(content)}".encode("utf-8")).hexdigest()[:20]
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM ask_conversations WHERE name = ?", (name,)).fetchone()
            if not row:
                return False
            conv_id = row["id"]
            conn.execute(
                """
                INSERT INTO ask_messages(id, conversation_id, role, content, model, token_limit, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, conv_id, role, content, model, token_limit, now),
            )
            conn.execute("UPDATE ask_conversations SET updated_at = ? WHERE id = ?", (now, conv_id))
            conn.commit()
            return True

    def migrate_legacy_json(self, json_path: Path) -> bool:
        if not json_path.exists():
            return False
        with self._connect() as conn:
            has_data = conn.execute("SELECT COUNT(*) AS c FROM ask_conversations").fetchone()["c"] > 0
        if has_data:
            return False
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return False
            chats = data.get("chats", {}) or {}
            active_chat = data.get("active_chat", "")
            for name, chat in chats.items():
                mode = (chat or {}).get("mode", "standard")
                self.create_conversation(name, mode=mode)
                for msg in (chat or {}).get("messages", []):
                    self.append_message(
                        name,
                        msg.get("role", "user"),
                        msg.get("content", ""),
                        model=msg.get("model", ""),
                        token_limit=int(msg.get("token_limit", 0) or 0),
                    )
            if active_chat:
                self.set_active_conversation(active_chat)
            backup = json_path.with_suffix(".migrated.backup.json")
            if not backup.exists():
                backup.write_text(json_path.read_text(encoding="utf-8"), encoding="utf-8")
            return True
        except (OSError, json.JSONDecodeError) as e:
            logger.error("[AskChatStore] migrate_legacy_json IO/parse error: %s", e)
            return False
        except (TypeError, ValueError) as e:
            logger.warning("[AskChatStore] migrate_legacy_json data shape error: %s", e)
            return False


_store_cache: Dict[str, "AskChatSQLiteAPI"] = {}
_store_lock = threading.Lock()


def get_ask_chat_store(data_dir: Optional[Path] = None) -> "AskChatSQLiteAPI":
    resolved = str((data_dir or ensure_ask_data_dir()).resolve())
    with _store_lock:
        if resolved not in _store_cache:
            _store_cache[resolved] = AskChatSQLiteAPI(data_dir=Path(resolved))
        return _store_cache[resolved]


def clear_ask_chat_store_cache() -> None:
    """Clear the store cache — for use in tests only."""
    with _store_lock:
        _store_cache.clear()
