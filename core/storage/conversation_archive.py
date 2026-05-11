from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.storage.ask_chat_store import get_ask_chat_store


@dataclass(frozen=True)
class ArchiveCard:
    conversation_id: str
    headline_summary: str
    summaries: list[dict[str, Any]]
    raw_tail: list[dict[str, Any]]
    total_tokens: int = 0


class ConversationArchive:
    def __init__(self, store=None) -> None:
        self.store = store or get_ask_chat_store()

    def fast_load(self, convo_id: str, *, raw_tail_limit: int = 80) -> ArchiveCard:
        archive = self.store.get_archive(convo_id) or {}
        summaries = self.store.list_summaries(convo_id)
        raw_tail = self.store.list_uncompacted_messages(convo_id, limit=raw_tail_limit)
        return ArchiveCard(
            conversation_id=convo_id,
            headline_summary=str(archive.get("headline_summary") or ""),
            summaries=summaries,
            raw_tail=raw_tail,
            total_tokens=int(archive.get("total_tokens") or 0),
        )


def fast_load(convo_id: str) -> ArchiveCard:
    return ConversationArchive().fast_load(convo_id)
