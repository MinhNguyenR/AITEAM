"""SQLite FTS5 + minimal edge store for context snapshots (GraphRAG v1)."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _fts5_escape_term(term: str) -> str:
    """Strip FTS5 special chars that can break MATCH syntax."""
    return re.sub(r'["\\\n\r\t]', "", term)


def _db_path() -> Path:
    p = Path.home() / ".ai-team" / "graphrag.sqlite"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_db_path()))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS doc_fts USING fts5(
            task_uuid UNINDEXED,
            kind UNINDEXED,
            path UNINDEXED,
            producer UNINDEXED,
            body,
            tokenize = 'unicode61'
        );
        CREATE TABLE IF NOT EXISTS rag_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            src TEXT NOT NULL,
            dst TEXT NOT NULL,
            relation TEXT NOT NULL,
            payload_json TEXT,
            ts TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_rag_edges_src ON rag_edges(src);
        CREATE INDEX IF NOT EXISTS idx_rag_edges_dst ON rag_edges(dst);
        """
    )
    conn.commit()


def delete_by_context_path(path: str | Path) -> None:
    p = str(Path(path).resolve())
    try:
        conn = _connect()
        _ensure_schema(conn)
        conn.execute("DELETE FROM doc_fts WHERE path = ?", (p,))
        conn.execute("DELETE FROM rag_edges WHERE dst = ?", (p,))
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        if "no such module" in str(e).lower() or "fts5" in str(e).lower():
            logger.warning("[graphrag] FTS5 unavailable: %s", e)
        else:
            logger.warning("[graphrag] delete_by_context_path: %s", e)
    except (OSError, sqlite3.Error, ValueError) as e:
        logger.warning("[graphrag] delete_by_context_path: %s", e)


def upsert_context_snapshot(
    task_uuid: str,
    text: str,
    *,
    kind: str = "context",
    path: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    meta = metadata or {}
    producer = str(meta.get("producer", ""))
    p = str(Path(path).resolve())
    body = text if len(text) <= 500_000 else text[:500_000]
    ts = datetime.now().isoformat()
    try:
        conn = _connect()
        _ensure_schema(conn)
        conn.execute("DELETE FROM doc_fts WHERE path = ?", (p,))
        conn.execute("DELETE FROM rag_edges WHERE dst = ?", (p,))
        conn.execute(
            "INSERT INTO doc_fts(task_uuid, kind, path, producer, body) VALUES (?,?,?,?,?)",
            (task_uuid or "", kind, p, producer, body),
        )
        if task_uuid:
            conn.execute(
                "INSERT INTO rag_edges(src, dst, relation, payload_json, ts) VALUES (?,?,?,?,?)",
                (task_uuid, p, "has_document", json.dumps({"kind": kind, "producer": producer}), ts),
            )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        if "no such module" in str(e).lower() or "fts5" in str(e).lower():
            logger.warning("[graphrag] FTS5 unavailable: %s", e)
        else:
            logger.warning("[graphrag] upsert_context_snapshot: %s", e)
    except (OSError, sqlite3.Error, TypeError, ValueError) as e:
        logger.warning("[graphrag] upsert_context_snapshot: %s", e)


def search_fts(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    terms = [_fts5_escape_term(t) for t in re.split(r"\W+", q, flags=re.UNICODE) if len(t) > 1][:8]
    terms = [t for t in terms if t]
    if not terms:
        return []
    match_q = " AND ".join(f'body: "{t}"' for t in terms)
    try:
        conn = _connect()
        _ensure_schema(conn)
        cur = conn.execute(
            "SELECT task_uuid, kind, path, producer, snippet(doc_fts, 4, '[', ']', '…', 32) AS snip "
            "FROM doc_fts WHERE doc_fts MATCH ? LIMIT ?",
            (match_q, max(1, min(limit, 100))),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except (OSError, sqlite3.Error, ValueError) as e:
        logger.warning("[graphrag] search_fts: %s", e)
        return []


def try_ingest_context_md(context_path: Path, state_data: dict, producer: str) -> None:
    p = Path(context_path)
    if not p.exists():
        return
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return
    if text.lstrip().upper().startswith("# NO_CONTEXT"):
        return
    tid = str(state_data.get("task_uuid") or "")
    upsert_context_snapshot(tid, text, kind="context", path=str(p), metadata={"producer": producer})


def neighbor_edges(node_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        conn = _connect()
        _ensure_schema(conn)
        cur = conn.execute(
            "SELECT src, dst, relation, payload_json, ts FROM rag_edges "
            "WHERE src = ? OR dst = ? LIMIT ?",
            (node_id, node_id, max(1, min(limit, 200))),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except (OSError, sqlite3.Error, ValueError) as e:
        logger.warning("[graphrag] neighbor_edges: %s", e)
        return []


def ingest_prompt_doc(
    task_uuid: str,
    role: str,
    stage: str,
    prompt_text: str,
    response_text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    meta = metadata or {}
    ts = datetime.now().isoformat()
    body = f"{prompt_text}\n---RESPONSE---\n{response_text}"
    if len(body) > 500_000:
        body = body[:500_000]
    path_key = f"prompt:{task_uuid}:{role}:{stage}"
    try:
        conn = _connect()
        _ensure_schema(conn)
        conn.execute("DELETE FROM doc_fts WHERE path = ?", (path_key,))
        conn.execute(
            "INSERT INTO doc_fts(task_uuid, kind, path, producer, body) VALUES (?,?,?,?,?)",
            (task_uuid or "", "prompt_doc", path_key, role, body),
        )
        if task_uuid:
            conn.execute(
                "INSERT INTO rag_edges(src, dst, relation, payload_json, ts) VALUES (?,?,?,?,?)",
                (task_uuid, path_key, "has_prompt", json.dumps({"role": role, "stage": stage, **meta}), ts),
            )
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        if "no such module" in str(e).lower() or "fts5" in str(e).lower():
            logger.warning("[graphrag] FTS5 unavailable: %s", e)
        else:
            logger.warning("[graphrag] ingest_prompt_doc: %s", e)
    except (OSError, sqlite3.Error, TypeError, ValueError) as e:
        logger.warning("[graphrag] ingest_prompt_doc: %s", e)


def search_similar_tasks(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    terms = [_fts5_escape_term(t) for t in re.split(r"\W+", q, flags=re.UNICODE) if len(t) > 1][:8]
    terms = [t for t in terms if t]
    if not terms:
        return []
    match_q = " AND ".join(f'body: "{t}"' for t in terms)
    try:
        conn = _connect()
        _ensure_schema(conn)
        cur = conn.execute(
            "SELECT task_uuid, kind, path, producer, snippet(doc_fts, 4, '[', ']', '…', 32) AS snip "
            "FROM doc_fts WHERE doc_fts MATCH ? AND kind = 'prompt_doc' LIMIT ?",
            (match_q, max(1, min(limit, 100))),
        )
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
    except (OSError, sqlite3.Error, ValueError) as e:
        logger.warning("[graphrag] search_similar_tasks: %s", e)
        return []


def ingest_workspace(*args: Any, **kwargs: Any) -> None:
    """Backward-compatible no-op workspace ingestion hook.

    Older code paths import this symbol from `core.storage` even when the
    workspace ingestion pipeline is not enabled in the current build.
    """

    logger.warning("[graphrag] ingest_workspace is unavailable in this build")


def search_graph(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Compatibility wrapper around `search_fts` for older callers."""

    return search_fts(query, limit=limit)


delete_by_path = delete_by_context_path
