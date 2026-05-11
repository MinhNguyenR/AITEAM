"""Storage package exports with lazy loading."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "AskChatSQLiteAPI": ("core.storage.ask_chat_store", "AskChatSQLiteAPI"),
    "get_ask_chat_store": ("core.storage.ask_chat_store", "get_ask_chat_store"),
    "delete_by_context_path": ("core.storage.graphrag_store", "delete_by_context_path"),
    "delete_by_path": ("core.storage.graphrag_store", "delete_by_path"),
    "ingest_prompt_doc": ("core.storage.graphrag_store", "ingest_prompt_doc"),
    "ingest_workspace": ("core.storage.graphrag_store", "ingest_workspace"),
    "neighbor_edges": ("core.storage.graphrag_store", "neighbor_edges"),
    "retrieve_hybrid": ("core.storage.graphrag_store", "retrieve_hybrid"),
    "search_fts": ("core.storage.graphrag_store", "search_fts"),
    "search_graph": ("core.storage.graphrag_store", "search_graph"),
    "search_similar_tasks": ("core.storage.graphrag_store", "search_similar_tasks"),
    "try_ingest_context_md": ("core.storage.graphrag_store", "try_ingest_context_md"),
    "upsert_context_snapshot": ("core.storage.graphrag_store", "upsert_context_snapshot"),
    "RerankClient": ("core.storage.rerank_client", "RerankClient"),
    "RerankResult": ("core.storage.rerank_client", "RerankResult"),
    "CompressedBrain": ("core.storage.knowledge_store", "CompressedBrain"),
    "extract_keywords": ("core.storage.knowledge_store", "extract_keywords"),
    "get_brain": ("core.storage.knowledge_store", "get_brain"),
    "smart_search": ("core.storage.knowledge_store", "smart_search"),
    "store_knowledge": ("core.storage.knowledge_store", "store_knowledge"),
}


def __getattr__(name: str) -> Any:
    if name in {"ask_history", "ask_chat_store", "code_backup", "graphrag_store", "knowledge_store", "rerank_client"}:
        return import_module(f"core.storage.{name}")
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module_name, attr = target
    value = getattr(import_module(module_name), attr)
    globals()[name] = value
    return value


__all__ = sorted([*_EXPORTS, "ask_history", "ask_chat_store", "code_backup", "graphrag_store", "knowledge_store", "rerank_client"])
