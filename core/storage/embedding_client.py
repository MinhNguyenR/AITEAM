from __future__ import annotations

import array
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from core.storage.memory_cost_guard import (
    estimate_tokens_local,
    get_memory_cost_guard,
    get_memory_worker_config,
    memory_home,
    memory_openrouter_api_key,
    memory_openrouter_base_url,
)
from core.storage.sqlite_utils import connect_wal

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EmbeddingResult:
    text_hash: str
    model: str
    vector: list[float]
    blob: bytes
    dim: int
    cached: bool = False


def _cache_key(text: str, model: str) -> str:
    return hashlib.sha256(f"{model}\n{text}".encode("utf-8")).hexdigest()


def vector_to_blob(vector: Iterable[float]) -> bytes:
    arr = array.array("f", [float(x) for x in vector])
    return arr.tobytes()


def blob_to_vector(blob: bytes) -> list[float]:
    arr = array.array("f")
    arr.frombytes(blob or b"")
    return [float(x) for x in arr]


class EmbeddingClient:
    def __init__(self, *, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else memory_home() / "graphrag.sqlite"
        cfg = get_memory_worker_config("MEMORY_EMBEDDING") or {}
        self.model = str(cfg.get("model") or "perplexity/pplx-embed-v1-0.6b")
        self.dim = int(cfg.get("dimensions") or 1024)
        self.provider = str(cfg.get("provider") or "openrouter")
        self.max_chars = _env_int("AI_TEAM_EMBED_MAX_CHARS", 24_000, minimum=256)
        self.cache_max_mb = _env_int("AI_TEAM_EMBED_CACHE_MAX_MB", 100, minimum=1)
        self._ensure_schema()

    def _connect(self):
        return connect_wal(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS embedding_cache (
                    text_hash TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    embedding BLOB NOT NULL,
                    dim INTEGER NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'openrouter',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def embed(self, text: str) -> EmbeddingResult:
        return self.embed_batch([text])[0]

    def embed_batch(self, texts: list[str], batch_size: int = 16) -> list[EmbeddingResult]:
        if not texts:
            return []
        texts = [self._prepare_text(text) for text in texts]
        results: list[EmbeddingResult | None] = [None] * len(texts)
        missing: list[tuple[int, str, str]] = []
        with self._connect() as conn:
            for idx, text in enumerate(texts):
                key = _cache_key(text, self.model)
                row = conn.execute("SELECT embedding, dim FROM embedding_cache WHERE text_hash = ? AND model = ?", (key, self.model)).fetchone()
                if row:
                    blob = bytes(row["embedding"])
                    results[idx] = EmbeddingResult(key, self.model, blob_to_vector(blob), blob, int(row["dim"]), cached=True)
                else:
                    missing.append((idx, key, text))
        for start in range(0, len(missing), max(1, int(batch_size))):
            chunk = missing[start : start + max(1, int(batch_size))]
            chunk_texts = [item[2] for item in chunk]
            input_tokens = sum(estimate_tokens_local(text) for text in chunk_texts)
            guard = get_memory_cost_guard()
            decision = guard.check(
                "embedding",
                role_key="MEMORY_EMBEDDING",
                model=self.model,
                input_tokens=input_tokens,
            )
            if not decision.allowed:
                guard.record(decision, status="blocked", metadata={"batch_size": len(chunk)})
                raise RuntimeError(f"memory embedding blocked: {decision.reason}")
            vectors = self._request_embeddings(chunk_texts)
            guard.record(decision, status="ok", metadata={"batch_size": len(chunk)})
            with self._connect() as conn:
                for (idx, key, _text), vector in zip(chunk, vectors):
                    blob = vector_to_blob(vector)
                    dim = len(vector)
                    conn.execute(
                        """
                        INSERT OR REPLACE INTO embedding_cache(text_hash, model, embedding, dim, provider, created_at)
                        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                        """,
                        (key, self.model, blob, dim, self.provider),
                    )
                    results[idx] = EmbeddingResult(key, self.model, vector, blob, dim, cached=False)
                conn.commit()
            self._evict_cache_if_needed()
        return [item for item in results if item is not None]

    def _request_embeddings(self, texts: list[str]) -> list[list[float]]:
        from openai import OpenAI

        api_key = memory_openrouter_api_key()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for embeddings")
        client = OpenAI(api_key=api_key, base_url=memory_openrouter_base_url())
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = client.embeddings.create(model=self.model, input=texts)
                return [[float(x) for x in item.embedding] for item in response.data]
            except Exception as exc:
                last_exc = exc
                if attempt >= 2:
                    break
                time.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"embedding request failed via OpenRouter model={self.model}: {last_exc}") from last_exc

    def _prepare_text(self, text: str) -> str:
        raw = str(text or "")
        if len(raw) <= self.max_chars:
            return raw
        head = self.max_chars // 2
        tail = self.max_chars - head
        return raw[:head] + "\n\n[...embedding input truncated...]\n\n" + raw[-tail:]

    def _evict_cache_if_needed(self) -> None:
        max_bytes = self.cache_max_mb * 1024 * 1024
        try:
            with self._connect() as conn:
                total = conn.execute("SELECT COALESCE(SUM(LENGTH(embedding)), 0) AS size FROM embedding_cache").fetchone()
                if int(total["size"] or 0) <= max_bytes:
                    return
                rows = conn.execute("SELECT text_hash, LENGTH(embedding) AS size FROM embedding_cache ORDER BY created_at ASC").fetchall()
                current = int(total["size"] or 0)
                for row in rows:
                    if current <= max_bytes:
                        break
                    conn.execute("DELETE FROM embedding_cache WHERE text_hash = ? AND model = ?", (row["text_hash"], self.model))
                    current -= int(row["size"] or 0)
                conn.commit()
        except Exception:
            logger.debug("[embedding] cache eviction skipped", exc_info=True)


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, value)


__all__ = ["EmbeddingClient", "EmbeddingResult", "blob_to_vector", "vector_to_blob"]
