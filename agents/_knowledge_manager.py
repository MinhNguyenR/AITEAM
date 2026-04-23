"""Knowledge retrieval via CompressedBrain — lazy-init, thread-safe."""
from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class KnowledgeManager:
    def __init__(self) -> None:
        self._brain = None
        self._lock = threading.Lock()

    @property
    def brain(self):
        if self._brain is None:
            with self._lock:
                if self._brain is None:
                    from core.storage import CompressedBrain
                    self._brain = CompressedBrain()
        return self._brain

    def search(self, agent_name: str, query: str, max_results: int = 3) -> List[Dict]:
        results = self.brain.smart_search(query, max_results)
        if results:
            logger.info("[%s] Found %d knowledge entries for: %s", agent_name, len(results), query[:50])
        return results

    def save(self, agent_name: str, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        cid = self.brain.store(title, content, tags)
        logger.info("[%s] Saved knowledge: '%s' → %s", agent_name, title, cid)
        return cid
