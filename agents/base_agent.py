"""
AI Agentic Framework v6.2 — Base Agent
=======================================
Abstract base class for ALL agents (Ambassador, Leader, Worker, Commander...).

Features:
  - OpenRouter API integration (auto-config from core.config)
  - Session memory (self.history)
  - CompressedBrain knowledge retrieval
  - Smart file reading (section-level, not full file)
  - Retry with exponential backoff (429 Rate Limit)
  - Budget guard (PAUSE signal on cost overflow)
  - Action logging to changelog.md

Author: Nguyễn Đặng Tường Minh
"""

import os
import time
import json
import logging
import re
import threading
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, Sequence, Union
from datetime import datetime
from pathlib import Path

from aiteam_bootstrap import ensure_project_root

_project_root = ensure_project_root()

from openai import OpenAI

from agents.llm_usage import chat_completions_create, chat_completions_create_stream, log_usage_event
from core.config import config
from core.config.constants import API_BASE_BACKOFF_SEC, API_MAX_RETRIES
from utils.budget_guard import DashboardBudgetExceeded, ensure_dashboard_budget_available
from utils.env_guard import redact_for_display

logger = logging.getLogger(__name__)


class BudgetExceeded(Exception):
    """Raised when agent cost exceeds configured budget limit."""
    pass


class BaseAgent(ABC):
    """
    Abstract base class for all AI agents in the framework.

    All agents inherit from this class and implement:
      - execute(task) → main work logic
      - format_output(response) → post-processing
    """

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
    ):
        """
        Initialize base agent.

        Args:
            agent_name: Human-readable name (e.g. "Worker A", "Commander")
            model_name: OpenRouter model ID (e.g. "deepseek/deepseek-v3.2")
            system_prompt: System instructions for this agent
            max_tokens: Max output tokens per API call (from config)
            temperature: Sampling temperature 0.0-1.0 (from config)
            budget_limit_usd: Max cost per session (None = unlimited)
        """
        self.agent_name = agent_name
        self.registry_role_key = (registry_role_key or "").strip()
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.budget_limit_usd = budget_limit_usd
        # Apply per-role prompt override (user-defined, never exposes original)
        try:
            from core.cli.state import get_prompt_overrides

            _role_key = agent_name.upper().replace(" ", "_")
            _overrides = get_prompt_overrides()
            if _role_key in _overrides:
                self.system_prompt = _overrides[_role_key]["prompt"]
        except (KeyError, TypeError, AttributeError):
            logger.warning("[%s] Invalid prompt override format; using default prompt", self.agent_name)

        # Session state
        self.history: List[Dict[str, str]] = []
        self.session_cost: float = 0.0
        self.session_calls: int = 0
        self.is_paused: bool = False

        # OpenRouter client (auto-config from core.config)
        self.client = OpenAI(
            api_key=config.api_key,
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
        )

        # CompressedBrain integration (lazy init)
        self._brain = None
        self._brain_lock = threading.Lock()

        # Project data directory
        self.data_dir = config.BASE_DIR
        self._extra_search_roots: List[Path] = (
            [Path(x) for x in extra_search_roots] if extra_search_roots else []
        )

        logger.info(f"[{self.agent_name}] Initialized with model: {self.model_name}")

    # ===== KNOWLEDGE RETRIEVAL =====

    @property
    def brain(self):
        """Lazy-init CompressedBrain instance."""
        if self._brain is None:
            with self._brain_lock:
                if self._brain is None:
                    from core.storage import CompressedBrain

                    self._brain = CompressedBrain()
        return self._brain

    def search_knowledge(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search CompressedBrain for relevant prior knowledge.

        Call this BEFORE call_api() to inject context from past work.

        Args:
            query: Natural language search query
            max_results: Max results to return

        Returns:
            List of dicts with id, title, tags, content, path
        """
        results = self.brain.smart_search(query, max_results)
        if results:
            logger.info(f"[{self.agent_name}] Found {len(results)} knowledge entries for: {query[:50]}")
        return results

    def save_knowledge(self, title: str, content: str, tags: Optional[List[str]] = None) -> str:
        """
        Save result to CompressedBrain for future agents.

        Args:
            title: Short descriptive title
            content: Full text content
            tags: Optional manual tags

        Returns:
            Content ID string
        """
        cid = self.brain.store(title, content, tags)
        logger.info(f"[{self.agent_name}] Saved knowledge: '{title}' → {cid}")
        return cid

    # ===== API COMMUNICATION =====

    def call_api(
        self,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Send prompt to OpenRouter API and get response.

        Features:
          - Auto-retry with exponential backoff on 429
          - Budget guard check before each call
          - Auto-append to conversation history
          - Output rules: concise, no greetings, no context repetition

        Args:
            user_prompt: The actual task/question
            model: Override model (default: self.model_name)
            max_tokens: Override max tokens
            temperature: Override temperature
            system_prompt: Override system prompt

        Returns:
            Response content string

        Raises:
            BudgetExceeded: If session cost exceeds budget_limit_usd
        """
        if self.is_paused:
            logger.warning(f"[{self.agent_name}] Agent is PAUSED — skipping API call")
            return "[PAUSED] Agent budget exceeded."

        try:
            ensure_dashboard_budget_available()
        except DashboardBudgetExceeded as e:
            logger.warning(f"[{self.agent_name}] {e}")
            return f"[PAUSED] {e}"

        # Budget guard
        self._check_budget()

        target_model = model or self.model_name
        target_tokens = max_tokens or self.max_tokens
        target_temp = temperature if temperature is not None else self.temperature
        target_system = system_prompt or self.system_prompt

        # Build messages
        messages = [
            {"role": "system", "content": target_system},
        ]
        messages.extend(self.history[-10:])  # Keep last 10 turns for context
        messages.append({"role": "user", "content": user_prompt})

        # Retry with exponential backoff
        last_error = None
        for attempt in range(self.MAX_RETRIES):
            try:
                resp = chat_completions_create(
                    self.client,
                    model=target_model,
                    messages=messages,
                    max_tokens=target_tokens,
                    temperature=target_temp,
                )

                # Debug: log response metadata
                usage = getattr(resp, "usage", None)
                finish_reason = resp.choices[0].finish_reason if resp.choices else "unknown"
                raw_prev = (resp.choices[0].message.content or "")[:100]
                content_preview = repr(redact_for_display(raw_prev)) if raw_prev else "EMPTY"
                logger.info(
                    f"[{self.agent_name}] Response: finish_reason={finish_reason}, "
                    f"content_preview={content_preview}, "
                    f"prompt_tokens={getattr(usage, 'prompt_tokens', 'N/A')}, "
                    f"completion_tokens={getattr(usage, 'completion_tokens', 'N/A')}"
                )

                content = resp.choices[0].message.content

                # Check finish_reason before anything else
                if finish_reason == "length":
                    prompt_tok = getattr(usage, "prompt_tokens", "?")
                    logger.warning(
                        f"[{self.agent_name}] finish_reason=length — output truncated "
                        f"(attempt {attempt+1}/{self.MAX_RETRIES}). "
                        f"prompt_tokens={prompt_tok}, max_tokens={target_tokens}."
                    )
                    # If this is the last attempt, raise so caller writes NO_CONTEXT
                    if attempt == self.MAX_RETRIES - 1:
                        raise ValueError(
                            f"[{self.agent_name}] Output truncated after {self.MAX_RETRIES} attempts "
                            f"(finish_reason=length, max_tokens={target_tokens})."
                        )
                    # Otherwise wait briefly and retry — model may succeed on next call
                    # (some providers are inconsistent with max_tokens enforcement)
                    last_error = ValueError(f"finish_reason=length attempt {attempt+1}")
                    time.sleep(self.BASE_BACKOFF * (2 ** attempt))
                    continue

                if not content or not content.strip():
                    # Truly empty — retry with backoff
                    last_error = ValueError(
                        f"API returned empty content "
                        f"(attempt {attempt+1}/{self.MAX_RETRIES}, finish_reason={finish_reason})"
                    )
                    logger.warning(f"[{self.agent_name}] {last_error}")
                    time.sleep(2 ** attempt)
                    continue

                content = content.strip()

                # Update history
                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": content})

                # Track cost (estimate from usage if available)
                usage = getattr(resp, "usage", None)
                prompt_tok      = getattr(usage, "prompt_tokens",     0) if usage else 0
                completion_tok  = getattr(usage, "completion_tokens", 0) if usage else 0
                if usage:
                    estimated_cost = self._estimate_cost(usage)
                    self.session_cost += estimated_cost
                    self.session_calls += 1
                    logger.debug(
                        f"[{self.agent_name}] Call #{self.session_calls} | "
                        f"in={prompt_tok} out={completion_tok} | "
                        f"Cost: ${estimated_cost:.5f} | Total: ${self.session_cost:.5f}"
                    )
                    log_usage_event(
                        {
                            "agent": self.agent_name,
                            "role_key": self.registry_role_key or self.agent_name,
                            "model": target_model,
                            "prompt_tokens": prompt_tok,
                            "completion_tokens": completion_tok,
                            "total_tokens": prompt_tok + completion_tok,
                            "cost_usd": estimated_cost,
                            "status": "ok",
                            "action": "chat.completions.create",
                            "finish_reason": finish_reason,
                        }
                    )

                return content

            except (OSError, RuntimeError, ValueError, TypeError) as e:
                last_error = e
                error_str = str(e).lower()

                # JSON decode error → response truncated, retry
                if "json" in error_str or "expecting value" in error_str:
                    logger.warning(
                        f"[{self.agent_name}] API response malformed (attempt {attempt+1}/{self.MAX_RETRIES})"
                    )
                    time.sleep(2 ** attempt)
                    continue

                # Rate limit → exponential backoff
                if "429" in error_str or "rate limit" in error_str:
                    wait = self.BASE_BACKOFF * (2 ** attempt)
                    logger.warning(
                        f"[{self.agent_name}] Rate limited — retry {attempt+1}/{self.MAX_RETRIES} "
                        f"in {wait:.1f}s"
                    )
                    time.sleep(wait)
                    continue

                # Other errors → fail immediately
                logger.error(f"[{self.agent_name}] API error: {e}")
                raise

        # All retries exhausted
        logger.error(f"[{self.agent_name}] All {self.MAX_RETRIES} retries failed")
        raise last_error

    def call_api_stream(
        self,
        user_prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Streaming chat completion; appends text chunks to workflow session for monitor TUI."""
        if self.is_paused:
            logger.warning(f"[{self.agent_name}] Agent is PAUSED — skipping API call")
            return "[PAUSED] Agent budget exceeded."
        try:
            ensure_dashboard_budget_available()
        except DashboardBudgetExceeded as e:
            logger.warning(f"[{self.agent_name}] {e}")
            return f"[PAUSED] {e}"
        self._check_budget()

        target_model = model or self.model_name
        target_tokens = max_tokens or self.max_tokens
        target_temp = temperature if temperature is not None else self.temperature
        target_system = system_prompt or self.system_prompt

        messages = [
            {"role": "system", "content": target_system},
        ]
        messages.extend(self.history[-10:])
        messages.append({"role": "user", "content": user_prompt})

        last_error: Optional[Exception] = None
        for attempt in range(self.MAX_RETRIES):
            try:
                stream = chat_completions_create_stream(
                    self.client,
                    model=target_model,
                    messages=messages,
                    max_tokens=target_tokens,
                    temperature=target_temp,
                )
                parts: List[str] = []
                usage_prompt = 0
                usage_completion = 0
                for chunk in stream:
                    u = getattr(chunk, "usage", None)
                    if u:
                        usage_prompt = int(getattr(u, "prompt_tokens", usage_prompt) or usage_prompt)
                        usage_completion = int(getattr(u, "completion_tokens", usage_completion) or usage_completion)
                    if not chunk.choices:
                        continue
                    delta = getattr(chunk.choices[0].delta, "content", None) or ""
                    if delta:
                        parts.append(delta)
                        try:
                            from core.cli.workflow import session as _ws

                            _ws.append_leader_stream_chunk(delta)
                        except LookupError:
                            pass
                content = "".join(parts).strip()
                if not content:
                    last_error = ValueError("stream returned empty content")
                    time.sleep(2**attempt)
                    continue

                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": content})
                if usage_prompt or usage_completion:
                    event = {
                        "model": target_model,
                        "prompt_tokens": usage_prompt,
                        "completion_tokens": usage_completion,
                    }
                    estimated_cost = self._estimate_cost_from_event(event)
                    self.session_cost += estimated_cost
                    self.session_calls += 1
                    log_usage_event(
                        {
                            "agent": self.agent_name,
                            "role_key": self.registry_role_key or self.agent_name,
                            "model": target_model,
                            "prompt_tokens": usage_prompt,
                            "completion_tokens": usage_completion,
                            "total_tokens": usage_prompt + usage_completion,
                            "cost_usd": estimated_cost,
                            "status": "ok",
                            "action": "chat.completions.stream",
                        }
                    )
                logger.info(f"[{self.agent_name}] stream done, len={len(content)}")
                return content
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                last_error = e
                err = str(e).lower()
                if "429" in err or "rate limit" in err:
                    wait = self.BASE_BACKOFF * (2**attempt)
                    logger.warning(f"[{self.agent_name}] stream rate limit — wait {wait:.1f}s")
                    time.sleep(wait)
                    continue
                logger.error(f"[{self.agent_name}] stream API error: {e}")
                raise
        if last_error:
            raise last_error
        raise RuntimeError("stream exhausted retries")

    def _estimate_cost(self, usage) -> float:
        prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
        completion_tokens = getattr(usage, "completion_tokens", 0) or 0
        event = {
            "model": self.model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        return self._estimate_cost_from_event(event)

    def _estimate_cost_from_event(self, event: Dict[str, Any]) -> float:
        from utils.tracker import compute_cost_usd

        agent_config = config.get_worker(self.agent_name.replace(" ", "_").upper())
        if agent_config and "pricing" in agent_config:
            p = agent_config["pricing"]
            event["price_input_m"] = p.get("input")
            event["price_output_m"] = p.get("output")
        return compute_cost_usd(event)

    def _check_budget(self):
        """Check if session cost exceeds budget limit. PAUSE if exceeded."""
        if self.budget_limit_usd and self.session_cost >= self.budget_limit_usd:
            self.is_paused = True
            logger.error(
                f"[{self.agent_name}] ⚠️ BUDGET EXCEEDED: "
                f"${self.session_cost:.4f} / ${self.budget_limit_usd:.2f} — PAUSING"
            )
            raise BudgetExceeded(
                f"Agent {self.agent_name} paused: cost ${self.session_cost:.4f} "
                f"exceeds limit ${self.budget_limit_usd:.2f}"
            )

    # ===== FILE & CONTEXT MANAGEMENT =====

    def read_project_file(self, file_name: str) -> Optional[str]:
        """
        Read a .md file from the project data directory (.ai-team/).

        Args:
            file_name: Filename (e.g. "context.md", "state.md", "summary.md")

        Returns:
            File content string or None if not found
        """
        candidate_name = Path(file_name)
        if candidate_name.is_absolute() or ".." in candidate_name.parts:
            logger.warning(f"[{self.agent_name}] Rejected unsafe file path: {file_name}")
            return None

        candidates = [self.data_dir / candidate_name, self.data_dir / "docs" / candidate_name]
        for root in self._extra_search_roots:
            candidates.append(root / candidate_name)
            candidates.append(root / "docs" / candidate_name)
        candidates.extend([_project_root / candidate_name, _project_root / "docs" / candidate_name])

        for path in candidates:
            if path.exists():
                content = path.read_text(encoding="utf-8")
                logger.info(f"[{self.agent_name}] Read file: {path}")
                return content

        logger.warning(f"[{self.agent_name}] File not found: {file_name}")
        return None

    def read_section(self, file_name: str, section_name: str) -> Optional[str]:
        """
        Read ONLY a specific section from a .md file (token-efficient).

        Sections are delimited by `## Section Name` markdown headers.

        Args:
            file_name: Filename (e.g. "context.md")
            section_name: Section header to extract (e.g. "Architecture")

        Returns:
            Section content or None if not found
        """
        content = self.read_project_file(file_name)
        if not content:
            return None

        # Match section header and capture until next ## header or EOF
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
        """
        Log an action to changelog.md for audit trail.

        Args:
            decision: What was decided
            action: What was done
            cost: Estimated cost of this action
        """
        changelog = self.data_dir / "changelog.md"

        # Ensure directory exists
        changelog.parent.mkdir(parents=True, exist_ok=True)

        entry = (
            f"### [{datetime.now().isoformat()}] {self.agent_name}\n"
            f"- **Decision:** {decision}\n"
            f"- **Action:** {action}\n"
            f"- **Cost:** ${cost:.4f}\n\n"
        )

        # Append mode — atomic, no race condition
        with self._changelog_lock:
            if not changelog.exists():
                changelog.write_text("# Changelog\n\n", encoding="utf-8")
            with open(changelog, "a", encoding="utf-8") as f:
                f.write(entry)

        logger.info(f"[{self.agent_name}] Logged action: {action[:50]}")

    # ===== SESSION MANAGEMENT =====

    def reset_session(self):
        """Clear conversation history and reset cost counters."""
        self.history.clear()
        self.session_cost = 0.0
        self.session_calls = 0
        self.is_paused = False
        logger.info(f"[{self.agent_name}] Session reset")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get current session statistics."""
        return {
            "agent": self.agent_name,
            "model": self.model_name,
            "calls": self.session_calls,
            "total_cost_usd": round(self.session_cost, 4),
            "history_length": len(self.history),
            "is_paused": self.is_paused,
        }

    # ===== ABSTRACT METHODS (must be implemented by subclasses) =====

    @abstractmethod
    def execute(self, task: str, **kwargs) -> str:
        """
        Main execution logic for this agent.

        Subclasses MUST implement this method.

        Args:
            task: The task description from Ambassador's DeltaBrief
            **kwargs: Additional context (files, previous results, etc.)

        Returns:
            Result string from the agent's work
        """
        pass

    @abstractmethod
    def format_output(self, response: str) -> str:
        """
        Post-process API response before returning.

        Subclasses MUST implement this method.
        Typical rules: remove greetings, strip markdown fences, enforce brevity.

        Args:
            response: Raw API response

        Returns:
            Cleaned, formatted output
        """
        pass

    # ===== UTILITY HELPERS =====

    def _strip_markdown_fences(self, text: str) -> str:
        """Remove ```language ... ``` fences from response."""
        # Strip opening fence (with optional language tag)
        text = re.sub(r"^```(?:\w+)?\n?", "", text.strip())
        # Strip closing fence
        text = re.sub(r"\n?```$", "", text)
        return text.strip()

    def _remove_greetings(self, text: str) -> str:
        """Remove common AI greeting phrases."""
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