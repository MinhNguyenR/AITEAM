"""Compact Worker — btw message mediator and state compressor at 262k token limit."""
from __future__ import annotations

import json
import logging
from typing import Any

from agents.base_agent import BaseAgent
from core.config import config

logger = logging.getLogger(__name__)

TOKEN_COMPACT_THRESHOLD = 262_000

_SYSTEM_PROMPT = """\
You are a Compact Worker. You have two responsibilities:

1. BTW Mediation: When the user sends a note or observation during an active pipeline run,
   synthesize their message with the current pipeline state and produce a concise, actionable
   note suitable for passing to the primary model on next context refresh.

2. State Compression: When the total token count approaches the 262k limit, compress the
   current pipeline state and activity log into a minimal, lossless summary that preserves
   all decisions, file paths, open questions, and next steps.

Always reply in the same language as the user's input. Be concise and structured.
Output ONLY the synthesized note or compressed summary — no preamble.
"""


class CompactWorker(BaseAgent):
    def __init__(self) -> None:
        cfg = config.get_worker("COMPACT_WORKER") or {}
        super().__init__(
            agent_name="CompactWorker",
            model_name=cfg.get("model", "openai/gpt-4.1-nano"),
            system_prompt=_SYSTEM_PROMPT,
            max_tokens=int(cfg.get("max_tokens", 2048)),
            temperature=float(cfg.get("temperature", 0.6)),
            registry_role_key="COMPACT_WORKER",
        )

    def execute(self, task: str, **kwargs: Any) -> str:
        return self.call_api(task)

    def format_output(self, response: str) -> str:
        return response.strip()

    def process_btw(self, message: str, state_summary: str) -> str:
        """Synthesize a user btw note with current pipeline state into an actionable note."""
        prompt = (
            f"Pipeline state summary:\n{state_summary[:3000]}\n\n"
            f"User note (btw): {message}\n\n"
            "Produce a concise 2-3 sentence synthesis that captures the user's intent "
            "and any action required, suitable for injecting into the primary model context."
        )
        try:
            return self.call_api(prompt)
        except Exception as e:
            logger.warning("[CompactWorker] process_btw failed: %s", e)
            return f"[btw note] {message}"

    def compress_state(self, state_json: str, activity_tail: str) -> str:
        """Compress pipeline state when token budget is near 262k."""
        prompt = (
            "The pipeline is approaching the 262k token limit. "
            "Compress the following state and activity log into a minimal summary "
            "that preserves all decisions, file paths, open questions, and next steps. "
            "Output ONLY the compressed summary — no preamble.\n\n"
            f"STATE:\n{state_json[:8000]}\n\n"
            f"ACTIVITY TAIL:\n{activity_tail[:4000]}"
        )
        try:
            return self.call_api(prompt)
        except Exception as e:
            logger.warning("[CompactWorker] compress_state failed: %s", e)
            return f"[compression failed: {e}]"

    def compact_conversation_range(self, convo_id: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        text = "\n".join(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in messages)
        prompt = (
            "Compress this conversation range into a durable memory summary. "
            "Return concise markdown with decisions, requirements, facts, open questions, and next steps. "
            "After the summary include JSON-like lines Topics: [...] and Entities: [...].\n\n"
            f"Conversation: {convo_id}\n{text[:12000]}"
        )
        try:
            body = self.call_api(prompt)
        except Exception as e:
            logger.warning("[CompactWorker] compact_conversation_range failed: %s", e)
            body = _fallback_summary(messages)
        return {"body": body.strip(), "topics": _extract_terms(body), "entities": _extract_terms(body)[:12]}

    def compact_summary_cards(self, convo_id: str, summaries: list[dict[str, Any]]) -> dict[str, Any]:
        text = "\n\n".join(str(s.get("body") or "") for s in summaries)
        prompt = (
            "Roll these memory summaries into one macro summary. Preserve durable facts, decisions, "
            "constraints, entities, and unresolved questions. Output markdown only.\n\n"
            f"Conversation: {convo_id}\n{text[:12000]}"
        )
        try:
            body = self.call_api(prompt)
        except Exception as e:
            logger.warning("[CompactWorker] compact_summary_cards failed: %s", e)
            body = text[:4000]
        return {"body": body.strip(), "topics": _extract_terms(body), "entities": _extract_terms(body)[:12]}


def _fallback_summary(messages: list[dict[str, Any]]) -> str:
    head = messages[0].get("content", "")[:500] if messages else ""
    tail = messages[-1].get("content", "")[:1000] if messages else ""
    return f"Conversation memory summary\n\nStart:\n{head}\n\nLatest:\n{tail}"


def _extract_terms(text: str) -> list[str]:
    import re

    seen: set[str] = set()
    out: list[str] = []
    for term in re.findall(r"\b[A-Za-zÀ-ỹ][\wÀ-ỹ-]{3,}\b", text or ""):
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(term)
        if len(out) >= 20:
            break
    return out


def build_state_summary_for_btw(snap: dict) -> str:
    """Build a short pipeline state summary for the CompactWorker process_btw call."""
    parts: list[str] = []
    tier = snap.get("brief_tier") or "unknown"
    active = snap.get("active_step") or "idle"
    paused = snap.get("paused_at_gate")
    buf = str(snap.get("leader_stream_buffer") or "")
    parts.append(f"tier={tier} active_step={active} paused={paused}")
    if buf:
        tail = buf[-1000:].replace("\n", " ").strip()
        parts.append(f"stream_tail: {tail}")
    nodes: list[dict] = snap.get("workflow_list_nodes_state") or []
    for n in nodes:
        s = n.get("status", "pending")
        nd = str(n.get("detail", ""))[:60]
        parts.append(f"  {n.get('node','?')}: {s}" + (f" — {nd}" if nd else ""))
    return "\n".join(parts)


__all__ = ["CompactWorker", "TOKEN_COMPACT_THRESHOLD", "build_state_summary_for_btw"]
