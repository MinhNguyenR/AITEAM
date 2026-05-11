from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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
class RerankResult:
    index: int
    relevance_score: float
    document: str = ""


def _cache_key(model: str, query: str, documents: list[str], top_n: int) -> str:
    digest = hashlib.sha256()
    digest.update(model.encode("utf-8"))
    digest.update(b"\n")
    digest.update(query.encode("utf-8"))
    digest.update(b"\n")
    digest.update(str(top_n).encode("ascii"))
    for doc in documents:
        digest.update(b"\n---doc---\n")
        digest.update(hashlib.sha256(str(doc or "").encode("utf-8")).hexdigest().encode("ascii"))
    return digest.hexdigest()


class RerankClient:
    def __init__(self, *, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else memory_home() / "graphrag.sqlite"
        cfg = get_memory_worker_config("MEMORY_RERANKER") or {}
        self.model = str(cfg.get("model") or "cohere/rerank-4-pro")
        self.provider = str(cfg.get("provider") or "openrouter")
        self.timeout = float(cfg.get("timeout") or 30)
        self.cache_enabled = bool(cfg.get("cache_enabled", True))
        self.doc_max_chars = _env_int("AI_TEAM_RERANK_DOC_MAX_CHARS", 2_000, minimum=200)
        self.total_max_chars = _env_int("AI_TEAM_RERANK_TOTAL_MAX_CHARS", 60_000, minimum=1_000)
        self._ensure_schema()

    def _connect(self):
        return connect_wal(self.db_path)

    def _ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rerank_cache (
                    cache_key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT 'openrouter',
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def rerank(self, query: str, documents: list[str], *, top_n: int = 12) -> list[RerankResult]:
        clean_docs = self._prepare_documents(documents)
        if not query.strip() or not clean_docs:
            return []
        top_n = max(1, min(int(top_n or 1), len(clean_docs)))
        key = _cache_key(self.model, query, clean_docs, top_n)
        if self.cache_enabled:
            cached = self._read_cache(key)
            if cached is not None:
                decision = get_memory_cost_guard().check(
                    "rerank",
                    role_key="MEMORY_RERANKER",
                    model=self.model,
                    input_tokens=0,
                )
                get_memory_cost_guard().record(decision, status="cache_hit", cached=True, metadata={"documents": len(clean_docs)})
                return cached
        input_tokens = estimate_tokens_local(query) + sum(estimate_tokens_local(doc) for doc in clean_docs)
        guard = get_memory_cost_guard()
        decision = guard.check("rerank", role_key="MEMORY_RERANKER", model=self.model, input_tokens=input_tokens)
        if not decision.allowed:
            guard.record(decision, status="blocked", metadata={"documents": len(clean_docs)})
            raise RuntimeError(f"memory rerank blocked: {decision.reason}")
        results = self._request_rerank(query, clean_docs, top_n=top_n)
        guard.record(decision, status="ok", metadata={"documents": len(clean_docs)})
        if self.cache_enabled:
            self._write_cache(key, results)
        return results

    def _read_cache(self, key: str) -> list[RerankResult] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT result_json FROM rerank_cache WHERE cache_key = ? AND model = ?", (key, self.model)).fetchone()
        if not row:
            return None
        try:
            raw = json.loads(str(row["result_json"] or "[]"))
            return [RerankResult(int(item["index"]), float(item["relevance_score"]), str(item.get("document") or "")) for item in raw]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    def _write_cache(self, key: str, results: list[RerankResult]) -> None:
        payload = json.dumps([result.__dict__ for result in results], ensure_ascii=False)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO rerank_cache(cache_key, model, provider, result_json, created_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """,
                (key, self.model, self.provider, payload),
            )
            conn.commit()

    def _request_rerank(self, query: str, documents: list[str], *, top_n: int) -> list[RerankResult]:
        api_key = memory_openrouter_api_key()
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is required for rerank")
        body = json.dumps(
            {
                "model": self.model,
                "query": query,
                "documents": documents,
                "top_n": top_n,
            },
            ensure_ascii=False,
        ).encode("utf-8")
        req = Request(
            f"{memory_openrouter_base_url().rstrip('/')}/rerank",
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/ai-team-blueprint",
                "X-Title": "ai-team memory reranker",
            },
            method="POST",
        )
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                with urlopen(req, timeout=self.timeout) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return self._parse_response(data)
            except HTTPError as exc:
                last_exc = exc
                if exc.code not in {408, 409, 425, 429, 500, 502, 503, 504} or attempt >= 2:
                    break
            except (URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
                last_exc = exc
                if attempt >= 2:
                    break
            time.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"rerank request failed via OpenRouter model={self.model}: {last_exc}") from last_exc

    def _parse_response(self, data: dict[str, Any]) -> list[RerankResult]:
        raw_results = data.get("results") if isinstance(data, dict) else None
        if not isinstance(raw_results, list):
            raw_results = data.get("data") if isinstance(data, dict) else None
        if not isinstance(raw_results, list):
            raise ValueError("rerank response missing results")
        results: list[RerankResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            if index is None and isinstance(item.get("document"), dict):
                index = item["document"].get("index")
            score = item.get("relevance_score", item.get("score", 0.0))
            if index is None:
                continue
            document = item.get("document")
            if isinstance(document, dict):
                document = document.get("text") or document.get("content") or ""
            results.append(RerankResult(index=int(index), relevance_score=float(score or 0.0), document=str(document or "")))
        return sorted(results, key=lambda result: result.relevance_score, reverse=True)

    def _prepare_documents(self, documents: list[str]) -> list[str]:
        out: list[str] = []
        used = 0
        for doc in documents:
            text = str(doc or "")
            if len(text) > self.doc_max_chars:
                text = text[: self.doc_max_chars]
            remaining = self.total_max_chars - used
            if remaining <= 0:
                break
            if len(text) > remaining:
                text = text[:remaining]
            out.append(text)
            used += len(text)
        return out


def _env_int(name: str, default: int, *, minimum: int) -> int:
    raw = os.getenv(name, "").strip()
    try:
        value = int(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, value)


__all__ = ["RerankClient", "RerankResult"]
