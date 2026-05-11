"""SQLite FTS5 + minimal edge store for context snapshots (GraphRAG v1)."""

from __future__ import annotations

import json
import logging
import math
import os
import re
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.storage.memory_cost_guard import memory_home
from core.storage.sqlite_utils import connect_wal

logger = logging.getLogger(__name__)


def _fts5_escape_term(term: str) -> str:
    """Strip FTS5 special chars that can break MATCH syntax."""
    return re.sub(r'["\\\n\r\t]', "", term)


def _db_path() -> Path:
    p = memory_home() / "graphrag.sqlite"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _connect() -> sqlite3.Connection:
    return connect_wal(_db_path(), foreign_keys=False)


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
        CREATE TABLE IF NOT EXISTS doc_embeddings (
            doc_id TEXT PRIMARY KEY,
            embedding BLOB NOT NULL,
            dim INTEGER NOT NULL,
            model TEXT NOT NULL,
            body_hash TEXT NOT NULL DEFAULT '',
            provider TEXT NOT NULL DEFAULT 'openrouter',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS embedding_cache (
            text_hash TEXT PRIMARY KEY,
            model TEXT NOT NULL,
            embedding BLOB NOT NULL,
            dim INTEGER NOT NULL,
            provider TEXT NOT NULL DEFAULT 'openrouter',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    _ensure_column(conn, "doc_embeddings", "body_hash", "TEXT NOT NULL DEFAULT ''")
    conn.commit()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
    cols = {str(row["name"]) for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


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
    embed: bool | None = None,
) -> None:
    meta = metadata or {}
    producer = str(meta.get("producer", ""))
    p = str(Path(path).resolve())
    body = text if len(text) <= 500_000 else text[:500_000]
    body_hash = _body_hash(body)
    embed_enabled = _should_embed_kind(kind, embed)
    ts = datetime.now().isoformat()
    try:
        conn = _connect()
        _ensure_schema(conn)
        embedding_current = _doc_embedding_current(conn, p, body_hash)
        conn.execute("DELETE FROM doc_fts WHERE path = ?", (p,))
        conn.execute("DELETE FROM rag_edges WHERE dst = ?", (p,))
        if not embedding_current:
            conn.execute("DELETE FROM doc_embeddings WHERE doc_id = ?", (p,))
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
        if embed_enabled and not embedding_current:
            _try_embed_doc(p, body, body_hash=body_hash)
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
    upsert_context_snapshot(tid, text, kind="context", path=str(p), metadata={"producer": producer}, embed=True)


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
    embed: bool | None = None,
) -> None:
    meta = metadata or {}
    ts = datetime.now().isoformat()
    body = f"{prompt_text}\n---RESPONSE---\n{response_text}"
    if len(body) > 500_000:
        body = body[:500_000]
    body_hash = _body_hash(body)
    embed_enabled = _should_embed_kind("prompt_doc", embed)
    path_key = f"prompt:{task_uuid}:{role}:{stage}"
    try:
        conn = _connect()
        _ensure_schema(conn)
        embedding_current = _doc_embedding_current(conn, path_key, body_hash)
        conn.execute("DELETE FROM doc_fts WHERE path = ?", (path_key,))
        if not embedding_current:
            conn.execute("DELETE FROM doc_embeddings WHERE doc_id = ?", (path_key,))
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
        if embed_enabled and not embedding_current:
            _try_embed_doc(path_key, body, body_hash=body_hash)
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


def _body_hash(body: str) -> str:
    return hashlib.sha256(str(body or "").encode("utf-8")).hexdigest()


def _should_embed_kind(kind: str, requested: bool | None) -> bool:
    if requested is not None:
        return bool(requested)
    normalized = str(kind or "").strip().lower()
    if normalized == "prompt_doc":
        return os.getenv("AI_TEAM_EMBED_PROMPT_DOCS", "").strip().lower() in {"1", "true", "yes", "on"}
    if normalized == "workflow_step":
        return False
    return normalized in {"context", "conversation_summary", "macro_summary", "conversation_archive"}


def _doc_embedding_current(conn: sqlite3.Connection, doc_id: str, body_hash: str) -> bool:
    try:
        row = conn.execute("SELECT body_hash FROM doc_embeddings WHERE doc_id = ?", (doc_id,)).fetchone()
        return bool(row and str(row["body_hash"] or "") == body_hash)
    except sqlite3.Error:
        return False


def _try_embed_doc(doc_id: str, body: str, *, body_hash: str = "") -> None:
    try:
        from core.storage.embedding_client import EmbeddingClient

        client = EmbeddingClient(db_path=_db_path())
        result = client.embed(body)
        conn = _connect()
        _ensure_schema(conn)
        conn.execute(
            """
            INSERT OR REPLACE INTO doc_embeddings(doc_id, embedding, dim, model, body_hash, provider, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doc_id, result.blob, result.dim, result.model, body_hash or _body_hash(body), "openrouter", datetime.now().isoformat()),
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.debug("[graphrag] embedding skipped for %s: %s", doc_id, e)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _vector_rows(query: str, limit: int = 50) -> list[dict[str, Any]]:
    try:
        from core.storage.embedding_client import EmbeddingClient, blob_to_vector

        conn = _connect()
        _ensure_schema(conn)
        count = conn.execute("SELECT COUNT(*) AS count FROM doc_embeddings").fetchone()
        if int((count or {})["count"] or 0) <= 0:
            conn.close()
            return []
        conn.close()
        q_vec = EmbeddingClient(db_path=_db_path()).embed(query).vector
        conn = _connect()
        _ensure_schema(conn)
        rows = conn.execute(
            """
            SELECT e.doc_id, e.embedding, f.task_uuid, f.kind, f.path, f.producer,
                   snippet(doc_fts, 4, '[', ']', '...', 32) AS snip
            FROM doc_embeddings e
            JOIN doc_fts f ON f.path = e.doc_id
            """
        ).fetchall()
        conn.close()
        scored: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            blob = bytes(item.pop("embedding") or b"")
            item["score"] = _cosine(q_vec, blob_to_vector(blob))
            scored.append(item)
        return sorted(scored, key=lambda item: float(item.get("score") or 0), reverse=True)[: max(1, limit)]
    except Exception as e:
        logger.debug("[graphrag] vector retrieval skipped: %s", e)
        return []


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, min(maximum, value))


def _rerank_mode(default: str = "auto") -> str:
    mode = os.getenv("AI_TEAM_RERANK_MODE", "").strip().lower() or default
    return mode if mode in {"auto", "always", "off"} else default


def _should_rerank(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    mode: str,
    role_key: str = "",
    importance: str = "normal",
) -> bool:
    if mode == "off" or len(candidates) < 8:
        return False
    if mode == "always":
        return True
    if importance.lower() == "important":
        return True
    role = role_key.upper()
    if any(token in role for token in ("LEADER", "TOOL_CURATOR", "WORKER", "REVIEWER", "FIXER")):
        return True
    q = query.lower()
    technical_terms = {
        "code",
        "bug",
        "traceback",
        "schema",
        "sqlite",
        "rag",
        "embedding",
        "rerank",
        "workflow",
        "agent",
        "terminal",
        "api",
        "test",
        "refactor",
        "implementation",
    }
    if any(term in q for term in technical_terms):
        return True
    return len(re.findall(r"\w+", query, flags=re.UNICODE)) >= 12


def _should_vector_search(query: str, *, role_key: str = "", importance: str = "normal") -> bool:
    mode = os.getenv("AI_TEAM_VECTOR_RETRIEVAL_MODE", "auto").strip().lower()
    if mode == "off":
        return False
    if mode == "always":
        return True
    if importance.lower() == "important":
        return True
    role = role_key.upper()
    if any(token in role for token in ("LEADER", "TOOL_CURATOR", "WORKER", "REVIEWER", "FIXER")):
        return True
    q = query.lower()
    return any(
        term in q
        for term in (
            "code",
            "bug",
            "traceback",
            "schema",
            "sqlite",
            "rag",
            "embedding",
            "workflow",
            "agent",
            "terminal",
            "api",
            "test",
            "refactor",
            "implementation",
        )
    )


def _load_candidate_bodies(candidates: list[dict[str, Any]], *, max_chars: int = 12_000) -> list[str]:
    keys = [str(item.get("path") or item.get("doc_id") or "") for item in candidates]
    keys = [key for key in keys if key]
    if not keys:
        return [str(item.get("snip") or "")[:max_chars] for item in candidates]
    try:
        placeholders = ",".join("?" for _ in keys)
        conn = _connect()
        _ensure_schema(conn)
        rows = conn.execute(f"SELECT path, body FROM doc_fts WHERE path IN ({placeholders})", tuple(keys)).fetchall()
        conn.close()
        bodies = {str(row["path"]): str(row["body"] or "")[:max_chars] for row in rows}
    except (OSError, sqlite3.Error, ValueError) as e:
        logger.debug("[graphrag] rerank body load skipped: %s", e)
        bodies = {}
    out: list[str] = []
    for item in candidates:
        key = str(item.get("path") or item.get("doc_id") or "")
        out.append((bodies.get(key) or str(item.get("snip") or ""))[:max_chars])
    return out


def _rerank_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    top_n: int,
) -> list[dict[str, Any]]:
    try:
        from core.storage.rerank_client import RerankClient

        docs = _load_candidate_bodies(candidates)
        client = RerankClient(db_path=_db_path())
        results = client.rerank(query, docs, top_n=min(top_n, len(candidates)))
    except Exception as e:
        logger.debug("[graphrag] rerank skipped: %s", e)
        return candidates
    reranked: list[dict[str, Any]] = []
    seen: set[int] = set()
    for result in results:
        if result.index < 0 or result.index >= len(candidates) or result.index in seen:
            continue
        seen.add(result.index)
        item = dict(candidates[result.index])
        item["rerank_score"] = result.relevance_score
        item["rerank_model"] = client.model
        item["retrieval_stage"] = "hybrid_reranked"
        reranked.append(item)
    for index, item in enumerate(candidates):
        if index not in seen:
            tail = dict(item)
            tail.setdefault("retrieval_stage", "hybrid")
            reranked.append(tail)
    return reranked


def retrieve_hybrid(
    query: str,
    k: int = 10,
    weights: tuple[float, float] = (0.5, 0.5),
    *,
    rerank: str = "auto",
    candidate_limit: int | None = None,
    top_n: int | None = None,
    role_key: str = "",
    importance: str = "normal",
) -> List[Dict[str, Any]]:
    mode = _rerank_mode(rerank)
    configured_candidates = _env_int("AI_TEAM_RERANK_CANDIDATES", candidate_limit or 50, minimum=30, maximum=80)
    configured_top_n = _env_int("AI_TEAM_RERANK_TOP_N", top_n or 12, minimum=1, maximum=15)
    bm25_rows = search_fts(query, limit=configured_candidates)
    vector_rows = _vector_rows(query, limit=configured_candidates) if _should_vector_search(query, role_key=role_key, importance=importance) else []
    if not vector_rows:
        candidates = bm25_rows[:configured_candidates]
        if _should_rerank(query, candidates, mode=mode, role_key=role_key, importance=importance):
            candidates = _rerank_candidates(query, candidates, top_n=configured_top_n)
        return candidates[: max(1, k)]
    scores: dict[str, float] = {}
    payloads: dict[str, dict[str, Any]] = {}
    w_bm25, w_vec = weights
    for rank, row in enumerate(bm25_rows, start=1):
        key = str(row.get("path") or "")
        if not key:
            continue
        scores[key] = scores.get(key, 0.0) + float(w_bm25) / (60 + rank)
        payloads.setdefault(key, dict(row))
    for rank, row in enumerate(vector_rows, start=1):
        key = str(row.get("path") or row.get("doc_id") or "")
        if not key:
            continue
        scores[key] = scores.get(key, 0.0) + float(w_vec) / (60 + rank)
        payloads.setdefault(key, dict(row))
    out: list[dict[str, Any]] = []
    for key, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)[:configured_candidates]:
        item = dict(payloads.get(key) or {})
        item["hybrid_score"] = score
        out.append(item)
    if _should_rerank(query, out, mode=mode, role_key=role_key, importance=importance):
        out = _rerank_candidates(query, out, top_n=configured_top_n)
    return out[: max(1, k)]


delete_by_path = delete_by_context_path
