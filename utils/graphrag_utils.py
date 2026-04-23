"""Best-effort GraphRAG ingestion helpers.

Safe to call even if graphrag_store is unavailable — failures are logged at
DEBUG level and never propagate to the caller.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


def try_ingest_context(
    context_path: Path,
    state_data: Dict[str, Any],
    producer: str,
) -> None:
    """Ingest a context.md file into the GraphRAG store if available."""
    try:
        from core.storage.graphrag_store import try_ingest_context_md

        try_ingest_context_md(context_path, state_data, producer)
    except (ImportError, OSError, ValueError, TypeError) as e:
        logger.debug("[graphrag_utils] ingest skipped for %s: %s", producer, e)


def try_ingest_prompt_doc(
    task_uuid: str,
    role: str,
    stage: str,
    prompt_text: str,
    response_text: str,
    metadata: Dict[str, Any] | None = None,
) -> None:
    """Store a prompt+response pair in the GraphRAG prompt store. Never raises."""
    try:
        from core.storage.graphrag_store import ingest_prompt_doc

        ingest_prompt_doc(task_uuid, role, stage, prompt_text, response_text, metadata)
    except (ImportError, OSError, ValueError, TypeError) as e:
        logger.debug("[graphrag_utils] prompt_doc ingest skipped for %s/%s: %s", role, stage, e)


__all__ = ["try_ingest_context", "try_ingest_prompt_doc"]
