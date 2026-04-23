"""Protocol for prompt document storage — replaceable by any custom backend."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PromptStoreProtocol(Protocol):
    def ingest_prompt_doc(
        self,
        task_uuid: str,
        role: str,
        stage: str,
        prompt_text: str,
        response_text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    def search_similar_tasks(
        self,
        query: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]: ...


__all__ = ["PromptStoreProtocol"]
