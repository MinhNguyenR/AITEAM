"""OpenRouter API client wrapper — retry, budget guard, stream aggregation."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from core.config.constants import API_BASE_BACKOFF_SEC, API_MAX_RETRIES
from utils.budget_guard import DashboardBudgetExceeded, ensure_dashboard_budget_available
from utils.env_guard import redact_for_display

logger = logging.getLogger(__name__)

_MAX_RETRIES = API_MAX_RETRIES
_BASE_BACKOFF = API_BASE_BACKOFF_SEC


def chat_completions_create(
    client: Any,
    *,
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
    temperature: float,
):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )


def chat_completions_create_stream(
    client: Any,
    *,
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
    temperature: float,
):
    return client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )


def log_usage_event(payload: Dict[str, Any]) -> None:
    try:
        from utils.tracker import append_usage_log

        append_usage_log(payload)
    except (OSError, ValueError) as e:
        logger.debug("Usage log skipped: %s", e)


class APIClient:
    """Handles all OpenRouter API calls for one agent session."""

    def __init__(
        self,
        *,
        client: Any,
        agent_name: str,
        model_name: str,
        max_tokens: int,
        temperature: float,
        registry_role_key: str,
        history: List[Dict],
        budget: Any,
        stream_chunk_callback=None,
    ) -> None:
        self.client = client
        self.agent_name = agent_name
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.registry_role_key = registry_role_key
        self.history = history
        self._budget = budget
        self._stream_chunk_callback = stream_chunk_callback

    def _build_messages(
        self, user_prompt: str, system_prompt: Optional[str], default_system: str
    ) -> List[Dict[str, str]]:
        target_system = system_prompt or default_system
        messages: List[Dict[str, str]] = [{"role": "system", "content": target_system}]
        messages.extend(self.history[-10:])
        messages.append({"role": "user", "content": user_prompt})
        return messages

    def _handle_response_content(
        self, resp: Any, attempt: int, target_tokens: int
    ) -> Optional[str]:
        usage = getattr(resp, "usage", None)
        finish_reason = resp.choices[0].finish_reason if resp.choices else "unknown"
        raw_prev = (resp.choices[0].message.content or "")[:100]
        content_preview = repr(redact_for_display(raw_prev)) if raw_prev else "EMPTY"
        logger.info(
            "[%s] Response: finish_reason=%s, content_preview=%s, prompt_tokens=%s, completion_tokens=%s",
            self.agent_name, finish_reason, content_preview,
            getattr(usage, "prompt_tokens", "N/A"),
            getattr(usage, "completion_tokens", "N/A"),
        )
        content = resp.choices[0].message.content
        if finish_reason == "length":
            prompt_tok = getattr(usage, "prompt_tokens", "?")
            logger.warning(
                "[%s] finish_reason=length — output truncated (attempt %d/%d). prompt_tokens=%s, max_tokens=%d.",
                self.agent_name, attempt + 1, _MAX_RETRIES, prompt_tok, target_tokens,
            )
            if attempt == _MAX_RETRIES - 1:
                raise ValueError(
                    f"[{self.agent_name}] Output truncated after {_MAX_RETRIES} attempts "
                    f"(finish_reason=length, max_tokens={target_tokens})."
                )
            return None
        if not content or not content.strip():
            logger.warning(
                "[%s] API returned empty content (attempt %d/%d, finish_reason=%s)",
                self.agent_name, attempt + 1, _MAX_RETRIES, finish_reason,
            )
            return None
        return content.strip()

    def _log_api_usage(
        self,
        prompt_tok: int,
        completion_tok: int,
        estimated_cost: float,
        target_model: str,
        action: str,
        finish_reason: str = "stop",
    ) -> None:
        logger.debug(
            "[%s] Call #%d | in=%d out=%d | Cost: $%.5f | Total: $%.5f",
            self.agent_name, self._budget.session_calls,
            prompt_tok, completion_tok, estimated_cost, self._budget.session_cost,
        )
        log_usage_event({
            "agent": self.agent_name,
            "role_key": self.registry_role_key or self.agent_name,
            "model": target_model,
            "prompt_tokens": prompt_tok,
            "completion_tokens": completion_tok,
            "total_tokens": prompt_tok + completion_tok,
            "cost_usd": estimated_cost,
            "status": "ok",
            "action": action,
            "finish_reason": finish_reason,
        })

    def _compute_call_cost(
        self, prompt_tokens: int, completion_tokens: int, model: str
    ) -> float:
        from utils.tracker import compute_cost_usd
        from core.config import config

        event: Dict[str, Any] = {
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        agent_cfg = config.get_worker(self.agent_name.replace(" ", "_").upper())
        if agent_cfg and "pricing" in agent_cfg:
            p = agent_cfg["pricing"]
            event["price_input_m"] = p.get("input")
            event["price_output_m"] = p.get("output")
        return compute_cost_usd(event)

    def _aggregate_stream(self, stream: Any) -> tuple:
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
                if self._stream_chunk_callback is not None:
                    try:
                        self._stream_chunk_callback(delta)
                    except Exception as _cb_err:
                        logger.debug("[%s] Stream callback error: %s", self.agent_name, type(_cb_err).__name__)
                else:
                    try:
                        from core.cli.workflow.runtime import session as _ws
                        _ws.append_leader_stream_chunk(delta)
                    except LookupError:
                        logger.debug("[%s] stream monitor not active, chunk dropped", self.agent_name)
        return "".join(parts).strip(), usage_prompt, usage_completion

    def call_api(
        self,
        user_prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        default_system: str,
    ) -> str:
        if self._budget.is_paused:
            logger.warning("[%s] Agent is PAUSED — skipping API call", self.agent_name)
            return "[PAUSED] Agent budget exceeded."
        try:
            ensure_dashboard_budget_available()
        except DashboardBudgetExceeded as e:
            logger.warning("[%s] %s", self.agent_name, e)
            return f"[PAUSED] {e}"
        self._budget.check()

        messages = self._build_messages(user_prompt, system_prompt, default_system)
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = chat_completions_create(
                    self.client,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content = self._handle_response_content(resp, attempt, max_tokens)
                if content is None:
                    last_error = ValueError(f"retry needed (attempt {attempt + 1})")
                    time.sleep(_BASE_BACKOFF * (2 ** attempt))
                    continue

                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": content})

                usage = getattr(resp, "usage", None)
                if usage:
                    prompt_tok = getattr(usage, "prompt_tokens", 0) or 0
                    completion_tok = getattr(usage, "completion_tokens", 0) or 0
                    cost = self._compute_call_cost(prompt_tok, completion_tok, model)
                    self._budget.session_cost += cost
                    self._budget.session_calls += 1
                    finish_reason = resp.choices[0].finish_reason if resp.choices else "stop"
                    self._log_api_usage(prompt_tok, completion_tok, cost, model, "chat.completions.create", finish_reason)

                return content

            except (OSError, RuntimeError, ValueError, TypeError) as e:
                last_error = e
                error_str = str(e).lower()
                if "json" in error_str or "expecting value" in error_str:
                    logger.warning("[%s] API response malformed (attempt %d/%d)", self.agent_name, attempt + 1, _MAX_RETRIES)
                    time.sleep(2 ** attempt)
                    continue
                if "429" in error_str or "rate limit" in error_str:
                    wait = _BASE_BACKOFF * (2 ** attempt)
                    logger.warning("[%s] Rate limited — retry %d/%d in %.1fs", self.agent_name, attempt + 1, _MAX_RETRIES, wait)
                    time.sleep(wait)
                    continue
                status = getattr(e, "status_code", getattr(e, "code", None))
                logger.error(
                    "[%s] API error: %s (status=%s)",
                    self.agent_name, type(e).__name__, status,
                )
                logger.debug("[%s] API error detail: %s", self.agent_name, e)
                raise

        logger.error("[%s] All %d retries failed", self.agent_name, _MAX_RETRIES)
        raise last_error

    def call_api_stream(
        self,
        user_prompt: str,
        *,
        model: str,
        max_tokens: int,
        temperature: float,
        system_prompt: Optional[str],
        default_system: str,
    ) -> str:
        if self._budget.is_paused:
            logger.warning("[%s] Agent is PAUSED — skipping API call", self.agent_name)
            return "[PAUSED] Agent budget exceeded."
        try:
            ensure_dashboard_budget_available()
        except DashboardBudgetExceeded as e:
            logger.warning("[%s] %s", self.agent_name, e)
            return f"[PAUSED] {e}"
        self._budget.check()

        messages = self._build_messages(user_prompt, system_prompt, default_system)
        last_error: Optional[Exception] = None
        for attempt in range(_MAX_RETRIES):
            try:
                stream = chat_completions_create_stream(
                    self.client,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                content, usage_prompt, usage_completion = self._aggregate_stream(stream)
                if not content:
                    last_error = ValueError("stream returned empty content")
                    time.sleep(2 ** attempt)
                    continue

                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": content})
                if usage_prompt or usage_completion:
                    cost = self._compute_call_cost(usage_prompt, usage_completion, model)
                    self._budget.session_cost += cost
                    self._budget.session_calls += 1
                    self._log_api_usage(usage_prompt, usage_completion, cost, model, "chat.completions.stream")
                logger.info("[%s] stream done, len=%d", self.agent_name, len(content))
                return content
            except (OSError, RuntimeError, ValueError, TypeError) as e:
                last_error = e
                err = str(e).lower()
                if "429" in err or "rate limit" in err:
                    wait = _BASE_BACKOFF * (2 ** attempt)
                    logger.warning("[%s] stream rate limit — wait %.1fs", self.agent_name, wait)
                    time.sleep(wait)
                    continue
                logger.error("[%s] stream API error: %s", self.agent_name, e)
                raise
        if last_error:
            raise last_error
        raise RuntimeError("stream exhausted retries")
