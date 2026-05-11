"""OpenRouter API client wrapper - retry, budget guard, stream aggregation."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from core.config.constants import API_BASE_BACKOFF_SEC, API_MAX_RETRIES
from utils.budget_guard import DashboardBudgetExceeded, ensure_dashboard_budget_available
from utils.env_guard import redact_for_display
from ._usage_logging import log_workflow_usage

logger = logging.getLogger(__name__)

_MAX_RETRIES = API_MAX_RETRIES
_BASE_BACKOFF = API_BASE_BACKOFF_SEC


# Re-exported here so APIClient tests can patch transport helpers at this module boundary.
from ._api_transport import (
    make_openai_client,
    chat_completions_create,
    chat_completions_create_stream,
    _parse_think_tags,
    _extract_cache_tokens,
    log_usage_event,
)
from ._stream_aggregator import aggregate_stream

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
        try:
            from core.storage._token_window import build_token_aware_window, estimate_tokens, memory_budget_tokens

            messages.extend(
                build_token_aware_window(
                    self.history,
                    [],
                    budget=memory_budget_tokens(),
                    system_prompt_tokens=estimate_tokens(target_system, model=self.model_name),
                    model=self.model_name,
                )
            )
        except Exception:
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
                "[%s] finish_reason=length - output truncated (attempt %d/%d). prompt_tokens=%s, max_tokens=%d.",
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
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
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
            "cache_read_tokens": cache_read_tokens,
            "cache_write_tokens": cache_write_tokens,
        })
        log_workflow_usage(self.registry_role_key or "", target_model, prompt_tok, completion_tok)

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
        content, pt, ct, cr, cw, clarif = aggregate_stream(
            stream, agent_name=self.agent_name, chunk_callback=self._stream_chunk_callback
        )
        self._last_clarif_answer = clarif
        return content, pt, ct, cr, cw

    def _cache_headers(self) -> Dict[str, str]:
        try:
            from core.config.registry import get_worker_config
            reg = get_worker_config(self.registry_role_key or "")
        except Exception:
            reg = None
        if not reg or not bool(reg.get("cache_enabled")):
            return {}
        headers = {"X-OpenRouter-Cache": "true"}
        ttl = int(reg.get("cache_ttl_seconds") or 300)
        ttl = max(1, min(ttl, 86400))
        headers["X-OpenRouter-Cache-TTL"] = str(ttl)
        if bool(reg.get("cache_clear")):
            headers["X-OpenRouter-Cache-Clear"] = "true"
        return headers

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
            logger.warning("[%s] Agent is PAUSED - skipping API call", self.agent_name)
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
                from core.runtime import session as _ws_mod
                if _ws_mod.is_pipeline_stop_requested():
                    return "[STOPPED]"
            except Exception:
                pass
            try:
                resp = chat_completions_create(
                    self.client,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    extra_headers=self._cache_headers(),
                )
                content = self._handle_response_content(resp, attempt, max_tokens)
                if content is None:
                    last_error = ValueError(f"retry needed (attempt {attempt + 1})")
                    try:
                        from core.runtime import session as _ws_mod
                        if _ws_mod.is_pipeline_stop_requested():
                            return "[STOPPED]"
                    except Exception:
                        pass
                    time.sleep(_BASE_BACKOFF * (2 ** attempt))
                    continue

                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": content})

                usage = getattr(resp, "usage", None)
                if usage:
                    prompt_tok = getattr(usage, "prompt_tokens", 0) or 0
                    completion_tok = getattr(usage, "completion_tokens", 0) or 0
                    cr, cw = _extract_cache_tokens(usage)
                    cost = self._compute_call_cost(prompt_tok, completion_tok, model)
                    self._budget.session_cost += cost
                    self._budget.session_calls += 1
                    finish_reason = resp.choices[0].finish_reason if resp.choices else "stop"
                    self._log_api_usage(
                        prompt_tok, completion_tok, cost, model, "chat.completions.create", finish_reason,
                        cache_read_tokens=cr, cache_write_tokens=cw,
                    )

                return content

            except Exception as e:
                last_error = e
                error_str = str(e).lower()
                if "json" in error_str or "expecting value" in error_str:
                    logger.warning("[%s] API response malformed (attempt %d/%d)", self.agent_name, attempt + 1, _MAX_RETRIES)
                    time.sleep(2 ** attempt)
                    continue
                if "429" in error_str or "rate limit" in error_str:
                    wait = _BASE_BACKOFF * (2 ** attempt)
                    logger.warning("[%s] Rate limited - retry %d/%d in %.1fs", self.agent_name, attempt + 1, _MAX_RETRIES, wait)
                    time.sleep(wait)
                    continue
                _net_kw = (
                    "network connection", "connection lost", "connection reset",
                    "broken pipe", "socket", "timed out", "timeout", "eof",
                    "apiconnection", "apierror", "api error", "network error",
                )
                _is_net = any(kw in error_str for kw in _net_kw)
                try:
                    import openai
                    _is_net = _is_net or isinstance(e, (openai.APIConnectionError,))
                except Exception:
                    pass
                if _is_net:
                    wait = min(_BASE_BACKOFF * (2 ** attempt), 30.0)
                    logger.warning("[%s] Network error - retry %d/%d in %.1fs: %s", self.agent_name, attempt + 1, _MAX_RETRIES, wait, type(e).__name__)
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
            logger.warning("[%s] Agent is PAUSED - skipping API call", self.agent_name)
            return "[PAUSED] Agent budget exceeded."
        try:
            ensure_dashboard_budget_available()
        except DashboardBudgetExceeded as e:
            logger.warning("[%s] %s", self.agent_name, e)
            return f"[PAUSED] {e}"
        self._budget.check()

        messages = self._build_messages(user_prompt, system_prompt, default_system)

        # Estimate prompt tokens for UI feedback before OpenRouter sends the final usage chunk
        try:
            from core.runtime import session as _ws_mod
            _ws_mod.reset_stream_token_counters()
            estimated_pt = sum(len(str(m.get("content", ""))) for m in messages) // 4
            _ws_mod.set_stream_prompt_tokens(estimated_pt)
        except Exception:
            pass

        # Look up reasoning config from model registry
        _reasoning_cfg: Optional[Dict] = None
        try:
            from core.config.registry import get_worker_config
            _reg = get_worker_config(self.registry_role_key or "")
            if _reg:
                _reasoning_cfg = _reg.get("reasoning")
        except Exception:
            pass

        last_error: Optional[Exception] = None
        _total_prompt_tok = 0
        _total_completion_tok = 0
        _total_cache_read = 0
        _total_cache_write = 0
        _clarif_rounds = 0
        attempt = 0
        while attempt < _MAX_RETRIES:
            try:
                from core.runtime import session as _ws_mod
                if _ws_mod.is_pipeline_stop_requested():
                    return "[STOPPED]"
            except Exception:
                pass
            try:
                stream = chat_completions_create_stream(
                    self.client,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    reasoning=_reasoning_cfg,
                    extra_headers=self._cache_headers(),
                )
                content, usage_prompt, usage_completion, cache_r, cache_w = self._aggregate_stream(stream)
                _total_prompt_tok += usage_prompt
                _total_completion_tok += usage_completion
                _total_cache_read += cache_r
                _total_cache_write += cache_w

                # Clarification re-call: leader asked a question instead of generating content
                _clarif = getattr(self, '_last_clarif_answer', None)
                if _clarif is not None and not content and _clarif_rounds < 2:
                    _clarif_rounds += 1
                    if _clarif != "__skip__":
                        messages.append({"role": "assistant", "content": "[clarification requested]"})
                        messages.append({"role": "user", "content": f"User clarification: {_clarif}\n\nNow generate the full context.md."})
                    else:
                        messages.append({"role": "user", "content": "Clarification skipped. Proceed with best assumptions and generate the full context.md now."})
                    logger.info("[%s] clarification answered (%s) - re-calling for context.md", self.agent_name, _clarif[:40] if _clarif else "skip")
                    # Reset stream buffer so TUI shows fresh content for the re-call
                    try:
                        from core.runtime import session as _ws_mod
                        _ws_mod.clear_leader_stream_buffer()
                        _ws_mod.reset_stream_token_counters()
                    except Exception:
                        pass
                    continue  # don't increment attempt

                if not content:
                    last_error = ValueError("stream returned empty content")
                    try:
                        from core.runtime import session as _ws_mod
                        if _ws_mod.is_pipeline_stop_requested():
                            return "[STOPPED]"
                    except Exception:
                        pass
                    time.sleep(2 ** attempt)
                    attempt += 1
                    continue

                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": content})
                if _total_prompt_tok or _total_completion_tok:
                    cost = self._compute_call_cost(_total_prompt_tok, _total_completion_tok, model)
                    self._budget.session_cost += cost
                    self._budget.session_calls += 1
                    self._log_api_usage(
                        _total_prompt_tok, _total_completion_tok, cost, model, "chat.completions.stream",
                        cache_read_tokens=_total_cache_read, cache_write_tokens=_total_cache_write,
                    )
                logger.info("[%s] stream done, len=%d", self.agent_name, len(content))
                return content
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if "429" in err or "rate limit" in err:
                    wait = _BASE_BACKOFF * (2 ** attempt)
                    logger.warning("[%s] stream rate limit - wait %.1fs", self.agent_name, wait)
                    time.sleep(wait)
                    attempt += 1
                    continue
                # Transient network/protocol errors - retry indefinitely with backoff
                _network_kw = (
                    "remote protocol", "incomplete", "reset by peer",
                    "connection reset", "broken pipe", "connection aborted",
                    "server disconnected", "sending complete", "iter_raw",
                    "peer closed", "stream error", "connection error",
                    "network connection", "connection lost", "network error",
                    "socket", "timed out", "timeout", "eof",
                    "apiconnection", "apierror", "api error",
                )
                _is_network = any(kw in err for kw in _network_kw)
                try:
                    import openai
                    _is_network = _is_network or isinstance(e, (openai.APIConnectionError, openai.APIStatusError))
                except Exception:
                    pass
                if _is_network:
                    # Capped backoff: max 30s between retries
                    wait = min(_BASE_BACKOFF * (2 ** attempt), 30.0)
                    logger.warning("[%s] network error (attempt %d) - retry in %.1fs: %s",
                                   self.agent_name, attempt + 1, wait, type(e).__name__)
                    time.sleep(wait)
                    attempt += 1
                    continue
                logger.error("[%s] stream API error: %s - %s", self.agent_name, type(e).__name__, e)
                raise
        if last_error:
            raise last_error
        raise RuntimeError("stream exhausted retries")
