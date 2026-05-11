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

from core.storage.sqlite_utils import connect_wal


class AskChatSQLiteAPI:
    """SQLite API for ask conversations and messages."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path.home() / ".ai-team" / "aiteam-cache" / "ask-data"
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
                token_count INTEGER NOT NULL DEFAULT 0,
                compacted_at TEXT NULL,
                summary_id TEXT NULL,
                settled_at TEXT NULL,
                ts TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES ask_conversations(id) ON DELETE CASCADE
            )
            """
        )
        self._ensure_columns(
            conn,
            "ask_messages",
            {
                "token_count": "INTEGER NOT NULL DEFAULT 0",
                "compacted_at": "TEXT NULL",
                "summary_id": "TEXT NULL",
                "settled_at": "TEXT NULL",
            },
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS ask_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_summaries (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                range_start_ts TEXT NOT NULL,
                range_end_ts TEXT NOT NULL,
                body TEXT NOT NULL,
                topics_json TEXT NOT NULL DEFAULT '[]',
                entities_json TEXT NOT NULL DEFAULT '[]',
                embedding_id TEXT NOT NULL DEFAULT '',
                level INTEGER NOT NULL DEFAULT 1,
                rolled_up_at TEXT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES ask_conversations(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_archives (
                conversation_id TEXT PRIMARY KEY,
                last_active_ts TEXT NOT NULL,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                headline_summary TEXT NOT NULL DEFAULT '',
                topics_json TEXT NOT NULL DEFAULT '[]',
                agents_involved_json TEXT NOT NULL DEFAULT '[]',
                archived_at TEXT NOT NULL,
                FOREIGN KEY(conversation_id) REFERENCES ask_conversations(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ask_conversations_updated ON ask_conversations(updated_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ask_messages_conv_ts ON ask_messages(conversation_id, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ask_messages_compacted ON ask_messages(conversation_id, compacted_at, ts)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_conversation_summaries_conv ON conversation_summaries(conversation_id, created_at)")
        conn.commit()

    def _ensure_columns(self, conn: sqlite3.Connection, table: str, columns: dict[str, str]) -> None:
        existing = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _connect(self) -> sqlite3.Connection:
        conn = connect_wal(self.db_path)
        try:
            self._ensure_schema(conn)
        except sqlite3.OperationalError as exc:
            if "readonly" not in str(exc).lower():
                conn.close()
                raise
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
                SELECT id, role, content, ts, model, token_limit, token_count, compacted_at, summary_id, settled_at
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

    def append_message(self, name: str, role: str, content: str, model: str = "", token_limit: int = 0, token_count: int = 0) -> bool | dict[str, Any]:
        now = datetime.now().isoformat()
        msg_id = hashlib.sha256(f"{name}:{role}:{now}:{len(content)}".encode("utf-8")).hexdigest()[:20]
        if not token_count:
            try:
                from core.storage._token_window import estimate_tokens

                token_count = estimate_tokens(content, model=model)
            except Exception:
                token_count = max(1, len(str(content or "")) // 4)
        with self._connect() as conn:
            row = conn.execute("SELECT id FROM ask_conversations WHERE name = ?", (name,)).fetchone()
            if not row:
                return False
            conv_id = row["id"]
            conn.execute(
                """
                INSERT INTO ask_messages(id, conversation_id, role, content, model, token_limit, token_count, ts)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (msg_id, conv_id, role, content, model, token_limit, int(token_count or 0), now),
            )
            conn.execute("UPDATE ask_conversations SET updated_at = ? WHERE id = ?", (now, conv_id))
            conn.commit()
            return {"message_id": msg_id, "conversation_id": conv_id, "ts": now, "token_count": int(token_count or 0)}

    def get_conversation_by_id(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, name, mode, created_at, updated_at FROM ask_conversations WHERE id = ?",
                (conversation_id,),
            ).fetchone()
        if not row:
            return None
        return self.get_conversation(str(row["name"]))

    def list_uncompacted_messages(self, conversation_id: str, *, limit: int = 1000) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, conversation_id, role, content, model, token_limit, token_count, ts
                FROM ask_messages
                WHERE conversation_id = ? AND compacted_at IS NULL
                ORDER BY ts ASC
                LIMIT ?
                """,
                (conversation_id, max(1, int(limit))),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_messages_compacted(self, conversation_id: str, message_ids: list[str], summary_id: str) -> None:
        if not message_ids:
            return
        now = datetime.now().isoformat()
        placeholders = ",".join("?" for _ in message_ids)
        with self._connect() as conn:
            conn.execute(
                f"""
                UPDATE ask_messages
                SET compacted_at = ?, summary_id = ?
                WHERE conversation_id = ? AND id IN ({placeholders})
                """,
                (now, summary_id, conversation_id, *message_ids),
            )
            conn.commit()

    def add_summary(
        self,
        conversation_id: str,
        *,
        body: str,
        range_start_ts: str,
        range_end_ts: str,
        topics: list[str] | None = None,
        entities: list[str] | None = None,
        embedding_id: str = "",
        level: int = 1,
    ) -> str:
        now = datetime.now().isoformat()
        summary_id = hashlib.sha256(f"{conversation_id}:{range_start_ts}:{range_end_ts}:{level}:{now}".encode("utf-8")).hexdigest()[:20]
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_summaries(
                    id, conversation_id, range_start_ts, range_end_ts, body,
                    topics_json, entities_json, embedding_id, level, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    summary_id,
                    conversation_id,
                    range_start_ts,
                    range_end_ts,
                    body,
                    json.dumps(topics or [], ensure_ascii=False),
                    json.dumps(entities or [], ensure_ascii=False),
                    embedding_id,
                    int(level),
                    now,
                ),
            )
            conn.commit()
        return summary_id

    def list_summaries(self, conversation_id: str, *, include_rolled_up: bool = False) -> List[Dict[str, Any]]:
        where = "conversation_id = ?"
        if not include_rolled_up:
            where += " AND rolled_up_at IS NULL"
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, conversation_id, range_start_ts, range_end_ts, body,
                       topics_json, entities_json, embedding_id, level, rolled_up_at, created_at
                FROM conversation_summaries
                WHERE {where}
                ORDER BY level DESC, created_at ASC
                """,
                (conversation_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_summaries_rolled_up(self, summary_ids: list[str]) -> None:
        if not summary_ids:
            return
        now = datetime.now().isoformat()
        placeholders = ",".join("?" for _ in summary_ids)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE conversation_summaries SET rolled_up_at = ? WHERE id IN ({placeholders})",
                (now, *summary_ids),
            )
            conn.commit()

    def upsert_archive(
        self,
        conversation_id: str,
        *,
        last_active_ts: str,
        total_tokens: int,
        headline_summary: str,
        topics: list[str] | None = None,
        agents_involved: list[str] | None = None,
    ) -> None:
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_archives(
                    conversation_id, last_active_ts, total_tokens, headline_summary,
                    topics_json, agents_involved_json, archived_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(conversation_id) DO UPDATE SET
                    last_active_ts=excluded.last_active_ts,
                    total_tokens=excluded.total_tokens,
                    headline_summary=excluded.headline_summary,
                    topics_json=excluded.topics_json,
                    agents_involved_json=excluded.agents_involved_json,
                    archived_at=excluded.archived_at
                """,
                (
                    conversation_id,
                    last_active_ts,
                    int(total_tokens),
                    headline_summary,
                    json.dumps(topics or [], ensure_ascii=False),
                    json.dumps(agents_involved or [], ensure_ascii=False),
                    now,
                ),
            )
            conn.commit()

    def get_archive(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM conversation_archives WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()
        return dict(row) if row else None

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
