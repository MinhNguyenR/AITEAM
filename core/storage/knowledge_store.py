from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from core.config.constants import AI_TEAM_HOME
from core.storage.knowledge.repository import KnowledgeRepository
from core.storage.knowledge.sqlite_repository import (
    SqliteKnowledgeRepository,
    _vault_unwrap as _vault_unwrap_impl,
    _vault_wrap as _vault_wrap_impl,
)
from core.storage.knowledge_text import extract_keywords

CompressedBrain = SqliteKnowledgeRepository

_brain_instance: Optional[SqliteKnowledgeRepository] = None


def _vault_wrap(compressed: bytes) -> bytes:
    try:
        from core.config import Config

        base = Path(Config.BASE_DIR)
    except (ImportError, AttributeError):
        base = AI_TEAM_HOME
    return _vault_wrap_impl(compressed, base)


def _vault_unwrap(raw: bytes) -> Optional[bytes]:
    try:
        from core.config import Config

        base = Path(Config.BASE_DIR)
    except (ImportError, AttributeError):
        base = AI_TEAM_HOME
    return _vault_unwrap_impl(raw, base)


def get_brain() -> SqliteKnowledgeRepository:
    global _brain_instance
    if _brain_instance is None:
        _brain_instance = SqliteKnowledgeRepository()
    return _brain_instance


def smart_search(query_text: str, max_results: int = 3) -> List[Dict]:
    return get_brain().smart_search(query_text, max_results)


def store_knowledge(title: str, content: str, tags: Optional[List[str]] = None) -> str:
    return get_brain().store(title, content, tags)


__all__ = [
    "CompressedBrain",
    "KnowledgeRepository",
    "SqliteKnowledgeRepository",
    "extract_keywords",
    "get_brain",
    "smart_search",
    "store_knowledge",
    "_vault_wrap",
    "_vault_unwrap",
]
