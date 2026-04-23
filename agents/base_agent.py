"""
AI Agentic Framework v6.2 — Base Agent
=======================================
Abstract base class for ALL agents (Ambassador, Leader, Worker, Commander...).
Delegates API calls to _api_client.APIClient, budget to _budget_manager.BudgetManager,
and knowledge retrieval to _knowledge_manager.KnowledgeManager.
"""

import logging
import re
import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Sequence, Union
from datetime import datetime
from pathlib import Path

from core.bootstrap import ensure_project_root

_project_root = ensure_project_root()

from openai import OpenAI

from core.config import config
from core.config.constants import API_BASE_BACKOFF_SEC, API_MAX_RETRIES

from agents._budget_manager import BudgetManager
from agents._api_client import APIClient
from agents._knowledge_manager import KnowledgeManager

logger = logging.getLogger(__name__)


def _default_prompt_resolver() -> dict:
    from core.cli.state import get_prompt_overrides
    return get_prompt_overrides()


class BudgetExceeded(Exception):
    """Raised when agent cost exceeds configured budget limit."""
    pass


class BaseAgent(ABC):
    MAX_RETRIES = API_MAX_RETRIES
    BASE_BACKOFF = API_BASE_BACKOFF_SEC
    _changelog_lock = threading.Lock()

    def __init__(
        self,
        agent_name: str,
        model_name: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        budget_limit_usd: Optional[float] = None,
        extra_search_roots: Optional[Sequence[Union[str, Path]]] = None,
        registry_role_key: Optional[str] = None,
        prompt_override_resolver=None,
        config_override=None,
        stream_chunk_callback=None,
    ):
        self.agent_name = agent_name
        self.registry_role_key = (registry_role_key or "").strip()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.budget_limit_usd = budget_limit_usd

        _config = config_override or config

        # Apply per-role prompt override (injectable for tests)
        _resolver = prompt_override_resolver or _default_prompt_resolver
        try:
            _role_key = agent_name.upper().replace(" ", "_")
            _overrides = _resolver()
            if _role_key in _overrides:
                self.system_prompt = _overrides[_role_key]["prompt"]
        except (KeyError, TypeError, AttributeError):
            logger.warning("[%s] Invalid prompt override format; using default prompt", self.agent_name)

        # Session history (shared by reference with APIClient)
        self.history: List[Dict[str, str]] = []

        # OpenRouter client kept as self.client for backward compat (Ambassador uses it directly)
        from core.config.settings import openrouter_base_url as _base_url
        self.client = OpenAI(
            api_key=_config.api_key,
            base_url=_base_url(),
        )

        # Composed helpers
        self._budget = BudgetManager(agent_name=agent_name, budget_limit_usd=budget_limit_usd)
        self._api = APIClient(
            client=self.client,
            agent_name=agent_name,
            model_name=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
            registry_role_key=self.registry_role_key,
            history=self.history,
            budget=self._budget,
            stream_chunk_callback=stream_chunk_callback,
        )
        self._km = KnowledgeManager()

        # Project data directory
        self.data_dir = _config.BASE_DIR
        self._extra_search_roots: List[Path] = (
            [Path(x) for x in extra_search_roots] if extra_search_roots else []
        )

        logger.info(f"[{self.agent_name}] Initialized with model: {self.model_name}")

    # ===== BACKWARD COMPAT PROPERTIES =====

    @property
    def session_cost(self) -> float:
        return self._budget.session_cost

    @session_cost.setter
    def session_cost(self, value: float) -> None:
        self._budget.session_cost = value

    @property
    def session_calls(self) -> int:
        return self._budget.session_calls

    @session_calls.setter
    def session_calls(self, value: int) -> None:
        self._budget.session_calls = value

    @property
    def is_paused(self) -> bool:
        return self._budget.is_paused

    @is_paused.setter
    def is_paused(self, value: bool) -> None:
        self._budget.is_paused = value

    # ===== KNOWLEDGE RETRIEVAL =====

    @property
    def brain(self):
        return self._km.brain

    def search_knowledge(self, query: str, max_results: int = 3) -> List[Dict]:
        return self._km.search(self.agent_name, query, max_results)

    def save_knowledge(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        return self._km.save(self.agent_name, title, content, tags)

    # ===== API COMMUNICATION — delegated to APIClient =====

    def _build_messages(self, user_prompt: str, system_prompt: Optional[str]) -> List[Dict[str, str]]:
        return self._api._build_messages(user_prompt, system_prompt, self.system_prompt)

    def _handle_response_content(self, resp: Any, attempt: int, target_tokens: int) -> Optional[str]:
        return self._api._handle_response_content(resp, attempt, target_tokens)

    def _log_api_usage(
        self,
        prompt_tok: int,
        completion_tok: int,
        estimated_cost: float,
        target_model: str,
        action: str,
        finish_reason: str = "stop",
    ) -> None:
        self._api._log_api_usage(prompt_tok, completion_tok, estimated_cost, target_model, action, finish_reason)

    def _aggregate_stream(self, stream: Any) -> tuple:
        return self._api._aggregate_stream(stream)

    def _compute_call_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None,
    ) -> float:
        return self._api._compute_call_cost(prompt_tokens, completion_tokens, model or self.model_name)

    def call_api(
        self,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        return self._api.call_api(
            user_prompt,
            model=model or self.model_name,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
            system_prompt=system_prompt,
            default_system=self.system_prompt,
        )

    def call_api_stream(
        self,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        return self._api.call_api_stream(
            user_prompt,
            model=model or self.model_name,
            max_tokens=max_tokens or self.max_tokens,
            temperature=temperature if temperature is not None else self.temperature,
            system_prompt=system_prompt,
            default_system=self.system_prompt,
        )

    def _check_budget(self):
        self._budget.check()

    # ===== FILE & CONTEXT MANAGEMENT =====

    def read_project_file(self, file_name: str) -> Optional[str]:
        candidate_name = Path(file_name)
        if candidate_name.is_absolute() or ".." in candidate_name.parts:
            logger.warning("[%s] Rejected unsafe file path: %s", self.agent_name, file_name)
            return None

        allowed_roots: List[Path] = [
            self.data_dir,
            self.data_dir / "docs",
            *[r for root in self._extra_search_roots for r in (root, root / "docs")],
            _project_root,
            _project_root / "docs",
        ]
        candidates = [root / candidate_name for root in allowed_roots]

        for path in candidates:
            if not path.exists():
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if not any(
                resolved.is_relative_to(r.resolve()) for r in allowed_roots if r.exists()
            ):
                logger.warning(
                    "[%s] Rejected symlink escaping allowed roots: %s → %s",
                    self.agent_name, path, resolved,
                )
                continue
            content = resolved.read_text(encoding="utf-8")
            logger.info("[%s] Read file: %s", self.agent_name, path)
            return content

        logger.warning("[%s] File not found: %s", self.agent_name, file_name)
        return None

    def read_section(self, file_name: str, section_name: str) -> Optional[str]:
        content = self.read_project_file(file_name)
        if not content:
            return None
        pattern = rf"^## {re.escape(section_name)}\s*\n(.*?)(?=^## |\Z)"
        match = re.search(pattern, content, re.MULTILINE | re.DOTALL)
        if match:
            section = match.group(1).strip()
            logger.info(f"[{self.agent_name}] Read section '{section_name}' from {file_name}")
            return section
        logger.warning(f"[{self.agent_name}] Section '{section_name}' not found in {file_name}")
        return None

    # ===== LOGGING & AUDIT =====

    def log_action(self, decision: str, action: str, cost: float = 0.0):
        changelog = self.data_dir / "changelog.md"
        entry = (
            f"### [{datetime.now().isoformat()}] {self.agent_name}\n"
            f"- **Decision:** {decision}\n"
            f"- **Action:** {action}\n"
            f"- **Cost:** ${cost:.4f}\n\n"
        )
        try:
            changelog.parent.mkdir(parents=True, exist_ok=True)
            with self._changelog_lock:
                if not changelog.exists():
                    changelog.write_text("# Changelog\n\n", encoding="utf-8")
                with open(changelog, "a", encoding="utf-8") as f:
                    f.write(entry)
            logger.info(f"[{self.agent_name}] Logged action: {action[:50]}")
        except OSError as e:
            logger.warning("[%s] log_action failed (audit trail gap): %s", self.agent_name, e)

    # ===== SESSION MANAGEMENT =====

    def reset_session(self):
        self.history.clear()
        self._budget.reset()
        logger.info(f"[{self.agent_name}] Session reset")

    def get_session_summary(self) -> Dict[str, Any]:
        return {
            "agent": self.agent_name,
            "model": self.model_name,
            "calls": self.session_calls,
            "total_cost_usd": round(self.session_cost, 4),
            "history_length": len(self.history),
            "is_paused": self.is_paused,
        }

    # ===== ABSTRACT METHODS =====

    @abstractmethod
    def execute(self, task: str, **kwargs) -> str:
        pass

    @abstractmethod
    def format_output(self, response: str) -> str:
        pass

    # ===== UTILITY HELPERS =====

    def _strip_markdown_fences(self, text: str) -> str:
        text = re.sub(r"^```(?:\w+)?\n?", "", text.strip())
        text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def _remove_greetings(self, text: str) -> str:
        greetings = [
            r"^(Sure,?\s*)?",
            r"^(Here is|Here's|Here are)\s+(the|your|a|an)\s+",
            r"^(Of course,?\s*)?",
            r"^(Certainly,?\s*)?",
            r"^I'd be happy to\s+",
            r"^Let me\s+",
            r"^I can help you with\s+",
        ]
        result = text
        for pattern in greetings:
            result = re.sub(pattern, "", result, flags=re.IGNORECASE)
        return result.strip()

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} name='{self.agent_name}' "
            f"model='{self.model_name}' calls={self.session_calls} "
            f"cost=${self.session_cost:.4f}>"
        )
