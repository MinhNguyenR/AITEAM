from __future__ import annotations

import hashlib
import logging
import os
import re
import sqlite3
import zlib
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from core.config.constants import VAULT_DECOMPRESS_MAX_BYTES
from core.storage.knowledge.vault_key import load_or_create_vault_key
from core.storage.knowledge_text import (
    extract_keywords,
    fts_match_expression,
    fts_token_terms,
    like_fallback_rows,
)

logger = logging.getLogger(__name__)

_VAULT_MAGIC = b"AITEAMF1"
_PRAGMAS = (
    "PRAGMA journal_mode=WAL",
    "PRAGMA synchronous=NORMAL",
    "PRAGMA busy_timeout=5000",
    "PRAGMA temp_store=MEMORY",
    "PRAGMA foreign_keys=ON",
)


def _vault_fernet_optional(base_dir: Path):
    key = load_or_create_vault_key(base_dir)
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet

        return Fernet(key.encode("ascii"))
    except (ImportError, ValueError, TypeError, AttributeError):
        logger.warning("AI_TEAM_VAULT_KEY is not a valid Fernet key")
        return None


class VaultMissingKeyError(RuntimeError):
    """Raised when the Fernet vault key is unavailable and unencrypted storage is disallowed."""


def _vault_wrap(compressed: bytes, base_dir: Path) -> bytes:
    f = _vault_fernet_optional(base_dir)
    if f is None:
        if os.getenv("AI_TEAM_ALLOW_UNENCRYPTED_VAULT", "").lower() in ("1", "true", "yes"):
            logger.warning("AI_TEAM_VAULT_KEY missing; storing knowledge vault data unencrypted (dev mode)")
            return compressed
        raise VaultMissingKeyError(
            "Vault encryption key unavailable. "
            "Set AI_TEAM_VAULT_KEY or AI_TEAM_ALLOW_UNENCRYPTED_VAULT=1 for dev/CI."
        )
    return _VAULT_MAGIC + f.encrypt(compressed)


def _vault_unwrap(raw: bytes, base_dir: Path) -> Optional[bytes]:
    if not raw.startswith(_VAULT_MAGIC):
        return raw
    f = _vault_fernet_optional(base_dir)
    if f is None:
        logger.warning("Encrypted vault blob but AI_TEAM_VAULT_KEY missing or invalid")
        return None
    try:
        return f.decrypt(raw[len(_VAULT_MAGIC):])
    except (ValueError, zlib.error, TypeError) as e:
        logger.warning("Vault decrypt failed: %s", e)
        return None


class SqliteKnowledgeRepository:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is not None:
            self.base_dir = Path(base_dir)
        else:
            from core.config import Config

            self.base_dir = Path(Config.BASE_DIR)
        self.vault_dir = self.base_dir / "vault"
        self.index_db = self.base_dir / "index.db"
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.vault_dir.mkdir(parents=True, exist_ok=True)
        self._fts_ok = True
        self._init_db()

    @contextmanager
    def _conn(self, *, write: bool = False):
        conn = sqlite3.connect(self.index_db, timeout=5.0)
        try:
            for p in _PRAGMAS:
                try:
                    conn.execute(p)
                except sqlite3.OperationalError:
                    pass
            if write:
                conn.isolation_level = None
                conn.execute("BEGIN IMMEDIATE")
            yield conn
            if write:
                conn.execute("COMMIT")
        except Exception:
            if write:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.OperationalError:
                    pass
            raise
        finally:
            conn.close()

    def _init_db(self):
        with self._conn(write=True) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_index (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                )
                """
            )
            cur.execute("CREATE INDEX IF NOT EXISTS idx_tags ON knowledge_index(tags)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_title ON knowledge_index(title)")
            cur.execute(
                "CREATE INDEX IF NOT EXISTS idx_updated_at ON knowledge_index(updated_at DESC)"
            )
            cur.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    title,
                    tags,
                    brain_id UNINDEXED,
                    tokenize = 'unicode61'
                )
                """
            )
        self._backfill_fts()
        with self._conn() as conn:
            try:
                conn.execute("SELECT 1 FROM knowledge_fts LIMIT 1")
            except sqlite3.OperationalError:
                self._fts_ok = False

    def _backfill_fts(self) -> None:
        with self._conn(write=True) as conn:
            cur = conn.cursor()
            try:
                cur.execute("SELECT brain_id FROM knowledge_fts")
                have = {r[0] for r in cur.fetchall()}
            except sqlite3.OperationalError:
                return
            cur.execute("SELECT id, title, tags FROM knowledge_index")
            for rid, title, tags in cur.fetchall():
                if rid not in have:
                    cur.execute(
                        "INSERT INTO knowledge_fts(title, tags, brain_id) VALUES (?,?,?)",
                        (title, tags or "", rid),
                    )

    def _generate_id(self, title: str, content: str) -> str:
        raw = f"{title}:{content[:200]}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def _compress_content(self, content: str) -> bytes:
        return zlib.compress(content.encode("utf-8"), level=9)

    def _decompress_content(self, data: bytes) -> str:
        decompressor = zlib.decompressobj()
        out = decompressor.decompress(data, VAULT_DECOMPRESS_MAX_BYTES + 1)
        if len(out) > VAULT_DECOMPRESS_MAX_BYTES or decompressor.unconsumed_tail:
            raise ValueError(
                f"vault content exceeds {VAULT_DECOMPRESS_MAX_BYTES} byte cap"
            )
        return out.decode("utf-8")

    def _save_vault_file(self, content_id: str, compressed_data: bytes) -> str:
        filepath = self.vault_dir / f"{content_id}.zbin"
        tmp_path = self.vault_dir / f"{content_id}.zbin.tmp"
        try:
            tmp_path.write_bytes(_vault_wrap(compressed_data, self.base_dir))
            os.replace(str(tmp_path), str(filepath))
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink()
            raise
        return str(filepath)

    def _load_vault_file(self, content_id: str) -> Optional[bytes]:
        filepath = self.vault_dir / f"{content_id}.zbin"
        if not filepath.exists():
            return None
        raw = filepath.read_bytes()
        return _vault_unwrap(raw, self.base_dir)

    def store(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        auto_keywords = extract_keywords(content, top_k=5)
        all_tags = list(set((tags or []) + auto_keywords))
        tags_str = ",".join(all_tags)
        content_id = self._generate_id(title, content)
        content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
        compressed = self._compress_content(content)
        vault_path = self._save_vault_file(content_id, compressed)
        now = datetime.now().isoformat()
        with self._conn(write=True) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT OR REPLACE INTO knowledge_index
                (id, title, tags, path, created_at, updated_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (content_id, title, tags_str, vault_path, now, now, content_hash),
            )
            cur.execute("DELETE FROM knowledge_fts WHERE brain_id = ?", (content_id,))
            cur.execute(
                "INSERT INTO knowledge_fts(title, tags, brain_id) VALUES (?,?,?)",
                (title, tags_str, content_id),
            )
        logger.info(f"Stored: '{title}' (ID: {content_id}, Tags: {all_tags})")
        return content_id

    def store_batch(
        self, items: Iterable[Tuple[str, str, Optional[List[str]]]]
    ) -> List[str]:
        prepared: List[tuple] = []
        ids: List[str] = []
        now = datetime.now().isoformat()
        for title, content, tags in items:
            auto_keywords = extract_keywords(content, top_k=5)
            all_tags = list(set((tags or []) + auto_keywords))
            tags_str = ",".join(all_tags)
            content_id = self._generate_id(title, content)
            content_hash = hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()
            compressed = self._compress_content(content)
            vault_path = self._save_vault_file(content_id, compressed)
            prepared.append((content_id, title, tags_str, vault_path, now, now, content_hash))
            ids.append(content_id)
        if not prepared:
            return []
        with self._conn(write=True) as conn:
            cur = conn.cursor()
            cur.executemany(
                """
                INSERT OR REPLACE INTO knowledge_index
                (id, title, tags, path, created_at, updated_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                prepared,
            )
            cur.executemany(
                "DELETE FROM knowledge_fts WHERE brain_id = ?",
                [(row[0],) for row in prepared],
            )
            cur.executemany(
                "INSERT INTO knowledge_fts(title, tags, brain_id) VALUES (?,?,?)",
                [(row[1], row[2], row[0]) for row in prepared],
            )
        return ids

    def retrieve(self, content_id: str) -> Optional[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, tags, path FROM knowledge_index WHERE id = ?",
                (content_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        content_id, title, tags_str, path = row
        compressed_data = self._load_vault_file(content_id)
        if compressed_data is None:
            return None
        content = self._decompress_content(compressed_data)
        return {
            "id": content_id,
            "title": title,
            "tags": tags_str.split(",") if tags_str else [],
            "content": content,
            "path": path,
        }

    def delete(self, content_id: str) -> bool:
        with self._conn(write=True) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_fts WHERE brain_id = ?", (content_id,))
            cur.execute("DELETE FROM knowledge_index WHERE id = ?", (content_id,))
            deleted = cur.rowcount > 0
        if deleted:
            filepath = self.vault_dir / f"{content_id}.zbin"
            if filepath.exists():
                filepath.unlink()
        return deleted

    def smart_search(self, query_text: str, max_results: int = 3) -> List[Dict]:
        if not query_text.strip():
            return []
        query_keywords = extract_keywords(query_text, top_k=5)
        if not query_keywords:
            query_keywords = re.findall(r"\b\w{3,}\b", query_text.lower())
        terms = fts_token_terms(query_keywords, query_text)
        if not terms:
            return []
        lim = max(30, max_results * 5)
        rows: List[tuple] = []
        match_q = fts_match_expression(terms)
        with self._conn() as conn:
            cur = conn.cursor()
            fts_failed = False
            if self._fts_ok and match_q:
                try:
                    cur.execute(
                        """
                        SELECT k.id, k.title, k.tags, k.path
                        FROM knowledge_fts f
                        JOIN knowledge_index k ON k.id = f.brain_id
                        WHERE f MATCH ?
                        ORDER BY k.updated_at DESC
                        LIMIT ?
                        """,
                        (match_q, lim),
                    )
                    rows = cur.fetchall()
                except sqlite3.OperationalError as e:
                    logger.debug("knowledge_fts MATCH failed: %s", e)
                    fts_failed = True
            if not rows and (fts_failed or not self._fts_ok or not match_q):
                rows = like_fallback_rows(cur, terms, lim)
        results: List[Dict] = []
        seen_ids = set()
        for content_id, title, tags_str, path in rows:
            if content_id in seen_ids or len(results) >= max_results:
                continue
            compressed_data = self._load_vault_file(content_id)
            if compressed_data is None:
                continue
            try:
                content = self._decompress_content(compressed_data)
                results.append(
                    {
                        "id": content_id,
                        "title": title,
                        "tags": tags_str.split(",") if tags_str else [],
                        "content": content,
                        "path": path,
                    }
                )
                seen_ids.add(content_id)
            except (ValueError, zlib.error, TypeError):
                continue
        return results

    def list_all(self) -> List[Dict]:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, title, tags, created_at FROM knowledge_index ORDER BY created_at DESC"
            )
            rows = cur.fetchall()
        return [
            {
                "id": row[0],
                "title": row[1],
                "tags": row[2].split(",") if row[2] else [],
                "created_at": row[3],
            }
            for row in rows
        ]

    def count(self) -> int:
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM knowledge_index")
            return int(cur.fetchone()[0])

    def get_stats(self) -> Dict:
        total_entries = self.count()
        vault_size = sum(f.stat().st_size for f in self.vault_dir.glob("*.zbin"))
        with self._conn() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tags FROM knowledge_index")
            all_tags = set()
            for row in cur.fetchall():
                if row[0]:
                    all_tags.update(row[0].split(","))
        return {
            "total_entries": total_entries,
            "vault_size_bytes": vault_size,
            "vault_size_mb": round(vault_size / (1024 * 1024), 2),
            "unique_tags": len(all_tags),
            "tags": sorted(all_tags),
            "base_dir": str(self.base_dir),
            "index_db": str(self.index_db),
            "vault_dir": str(self.vault_dir),
        }

    def clear_all(self) -> None:
        with self._conn(write=True) as conn:
            cur = conn.cursor()
            try:
                cur.execute("DELETE FROM knowledge_fts")
            except sqlite3.OperationalError:
                pass
            cur.execute("DELETE FROM knowledge_index")
        for f in self.vault_dir.glob("*.zbin"):
            f.unlink()


__all__ = ["SqliteKnowledgeRepository", "_vault_wrap", "_vault_unwrap"]
