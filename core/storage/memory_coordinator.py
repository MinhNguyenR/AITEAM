from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any

from core.storage._token_window import build_token_aware_window, estimate_tokens, raw_compact_chunk_tokens, total_message_tokens
from core.storage.ask_chat_store import get_ask_chat_store
from core.storage.memory_cost_guard import estimate_tokens_local, get_memory_cost_guard

logger = logging.getLogger(__name__)
_LAST_COMPACT_AT: dict[str, float] = {}


class MemoryCoordinator:
    def __init__(self, *, store=None, settler=None) -> None:
        self.store = store or get_ask_chat_store()
        self.settler = settler

    def on_message(self, convo_id: str, message_id: str | None = None) -> None:
        if not convo_id:
            return
        self._maybe_compact(convo_id)
        self._maybe_rollup_summaries(convo_id)
        if self.settler is None:
            from core.storage.memory_settler import get_settler

            self.settler = get_settler()
        self.settler.reset(convo_id)

    def on_workflow_step(self, thread_id: str, payload: dict[str, Any]) -> None:
        if not thread_id:
            return
        body = json.dumps(payload, ensure_ascii=False, default=str)
        try:
            from core.storage.graphrag_store import upsert_context_snapshot

            upsert_context_snapshot(
                thread_id,
                body,
                kind="workflow_step",
                path=f"workflow:{thread_id}:{payload.get('node','step')}",
                metadata={"producer": "workflow"},
                embed=False,
            )
        except Exception as e:
            logger.debug("[memory] workflow step ingest skipped: %s", e)

    def build_context_window(
        self,
        convo_id: str,
        *,
        messages: list[dict[str, Any]] | None = None,
        budget: int | None = None,
        system_prompt_tokens: int = 0,
        model: str = "",
        query: str = "",
        role_key: str = "",
        importance: str = "normal",
    ) -> list[dict[str, str]]:
        if messages is None:
            conv = self.store.get_conversation_by_id(convo_id)
            messages = (conv or {}).get("messages") or []
        summaries = self.store.list_summaries(convo_id)
        window = build_token_aware_window(messages or [], summaries, budget=budget, system_prompt_tokens=system_prompt_tokens, model=model)
        retrieved = self._retrieve_relevant_memory(query, role_key=role_key, importance=importance)
        return retrieved + window

    def _retrieve_relevant_memory(self, query: str, *, role_key: str = "", importance: str = "normal") -> list[dict[str, str]]:
        q = str(query or "").strip()
        if not q:
            return []
        try:
            from core.storage.graphrag_store import retrieve_hybrid

            hits = retrieve_hybrid(q, k=8, rerank="auto", role_key=role_key, importance=importance)
        except Exception as exc:
            logger.debug("[memory] hybrid retrieval skipped: %s", exc)
            return []
        lines: list[str] = []
        for hit in hits:
            path = str(hit.get("path") or hit.get("doc_id") or "")
            snippet = str(hit.get("snip") or "").replace("\n", " ").strip()
            if not path and not snippet:
                continue
            score = hit.get("rerank_score", hit.get("hybrid_score", ""))
            score_text = f" score={score:.4f}" if isinstance(score, float) else ""
            lines.append(f"- {path}{score_text}: {snippet[:500]}")
        if not lines:
            return []
        return [{"role": "system", "content": "[retrieved memory]\n" + "\n".join(lines)}]

    def force_compact(self, convo_id: str) -> str:
        messages = self.store.list_uncompacted_messages(convo_id, limit=10_000)
        if not messages:
            return ""
        return self._compact_messages(convo_id, messages)

    def force_settle(self, convo_id: str) -> None:
        tail = self.store.list_uncompacted_messages(convo_id, limit=10_000)
        if tail:
            self._compact_messages(convo_id, tail)
        conv = self.store.get_conversation_by_id(convo_id) or {}
        messages = conv.get("messages") or []
        summaries = self.store.list_summaries(convo_id)
        total = total_message_tokens(messages)
        headline = "\n\n".join(str(s.get("body") or "") for s in summaries[-3:])[:4000]
        if not headline and messages:
            headline = str(messages[-1].get("content") or "")[:1000]
        self.store.upsert_archive(
            convo_id,
            last_active_ts=str(conv.get("updated_at") or datetime.now().isoformat()),
            total_tokens=total,
            headline_summary=headline,
            topics=[],
            agents_involved=sorted({str(m.get("role") or "") for m in messages if m.get("role")}),
        )
        try:
            from core.storage.graphrag_store import upsert_context_snapshot

            upsert_context_snapshot(convo_id, headline, kind="conversation_archive", path=f"archive:{convo_id}", metadata={"producer": "memory_settler"}, embed=True)
        except Exception as e:
            logger.debug("[memory] archive ingest skipped: %s", e)

    def _maybe_compact(self, convo_id: str) -> None:
        messages = self.store.list_uncompacted_messages(convo_id, limit=10_000)
        if total_message_tokens(messages) >= raw_compact_chunk_tokens():
            if not self._compact_cooldown_elapsed(convo_id):
                return
            self._compact_messages(convo_id, messages)

    def _compact_messages(self, convo_id: str, messages: list[dict[str, Any]]) -> str:
        if not messages:
            return ""
        input_tokens = sum(int(m.get("token_count") or 0) or estimate_tokens_local(str(m.get("content") or "")) for m in messages)
        guard = get_memory_cost_guard()
        decision = guard.check(
            "compact",
            role_key="COMPACT_WORKER",
            model="",
            input_tokens=input_tokens,
        )
        if not decision.allowed:
            guard.record(decision, status="blocked", metadata={"conversation_id": convo_id, "messages": len(messages)})
            result = {
                "body": self._fallback_message_summary(messages),
                "topics": [],
                "entities": [],
            }
        else:
            guard.record(decision, status="allowed", metadata={"conversation_id": convo_id, "messages": len(messages)})
            try:
                from agents.compact_worker import CompactWorker

                result = CompactWorker().compact_conversation_range(convo_id, messages)
                guard.record(decision, status="ok", metadata={"conversation_id": convo_id, "messages": len(messages)})
            except Exception as exc:
                logger.warning("[memory] compact worker unavailable; using fallback summary: %s", exc)
                guard.record(decision, status="fallback", metadata={"conversation_id": convo_id, "messages": len(messages)})
                result = {
                    "body": self._fallback_message_summary(messages),
                    "topics": [],
                    "entities": [],
                }
        _LAST_COMPACT_AT[convo_id] = time.time()
        summary_id = self.store.add_summary(
            convo_id,
            body=str(result.get("body") or ""),
            range_start_ts=str(messages[0].get("ts") or ""),
            range_end_ts=str(messages[-1].get("ts") or ""),
            topics=list(result.get("topics") or []),
            entities=list(result.get("entities") or []),
            level=1,
        )
        self.store.mark_messages_compacted(convo_id, [str(m.get("id") or "") for m in messages], summary_id)
        try:
            from core.storage.graphrag_store import upsert_context_snapshot

            upsert_context_snapshot(convo_id, str(result.get("body") or ""), kind="conversation_summary", path=f"summary:{summary_id}", metadata={"producer": "compact_worker"}, embed=True)
        except Exception as e:
            logger.debug("[memory] summary ingest skipped: %s", e)
        return summary_id

    def _maybe_rollup_summaries(self, convo_id: str) -> None:
        summaries = [s for s in self.store.list_summaries(convo_id) if int(s.get("level") or 1) <= 1]
        total = sum(estimate_tokens(str(s.get("body") or "")) for s in summaries)
        if total < 120_000 or len(summaries) < 3:
            return
        guard = get_memory_cost_guard()
        decision = guard.check("summary_rollup", role_key="COMPACT_WORKER", model="", input_tokens=total)
        if not decision.allowed:
            guard.record(decision, status="blocked", metadata={"conversation_id": convo_id, "summaries": len(summaries)})
            roll = {"body": "\n\n".join(str(s.get("body") or "") for s in summaries[:-1])[:4000], "topics": [], "entities": []}
        else:
            guard.record(decision, status="allowed", metadata={"conversation_id": convo_id, "summaries": len(summaries)})
            try:
                from agents.compact_worker import CompactWorker

                roll = CompactWorker().compact_summary_cards(convo_id, summaries[:-1])
                guard.record(decision, status="ok", metadata={"conversation_id": convo_id, "summaries": len(summaries)})
            except Exception as exc:
                logger.warning("[memory] summary rollup fallback: %s", exc)
                guard.record(decision, status="fallback", metadata={"conversation_id": convo_id, "summaries": len(summaries)})
                roll = {"body": "\n\n".join(str(s.get("body") or "") for s in summaries[:-1])[:4000], "topics": [], "entities": []}
        summary_id = self.store.add_summary(
            convo_id,
            body=str(roll.get("body") or ""),
            range_start_ts=str(summaries[0].get("range_start_ts") or ""),
            range_end_ts=str(summaries[-2].get("range_end_ts") or ""),
            topics=list(roll.get("topics") or []),
            entities=list(roll.get("entities") or []),
            level=2,
        )
        self.store.mark_summaries_rolled_up([str(s.get("id") or "") for s in summaries[:-1]])
        try:
            from core.storage.graphrag_store import upsert_context_snapshot

            upsert_context_snapshot(convo_id, str(roll.get("body") or ""), kind="macro_summary", path=f"summary:{summary_id}", metadata={"producer": "compact_worker"}, embed=True)
        except Exception:
            pass

    def _compact_cooldown_elapsed(self, convo_id: str) -> bool:
        cooldown = _env_float("AI_TEAM_COMPACT_COOLDOWN_SECONDS", 60.0, minimum=0.0)
        if cooldown <= 0:
            return True
        last = _LAST_COMPACT_AT.get(convo_id, 0.0)
        return time.time() - last >= cooldown

    def _fallback_message_summary(self, messages: list[dict[str, Any]]) -> str:
        if not messages:
            return "Empty conversation range."
        first = str(messages[0].get("content") or "")[:1000]
        last = str(messages[-1].get("content") or "")[:1500]
        return f"Conversation memory summary\n\nFirst message excerpt:\n{first}\n\nLatest message excerpt:\n{last}"


def _env_float(name: str, default: float, *, minimum: float) -> float:
    raw = os.getenv(name, "").strip()
    try:
        value = float(raw) if raw else default
    except ValueError:
        value = default
    return max(minimum, value)
