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


def make_openai_client(api_key: str, base_url: str) -> Any:
    from openai import OpenAI
    return OpenAI(api_key=api_key, base_url=base_url)


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
    reasoning: Optional[Dict] = None,
):
    kwargs: Dict[str, Any] = dict(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )
    if reasoning:
        kwargs["extra_body"] = {"reasoning": reasoning}
    return client.chat.completions.create(**kwargs)


def _parse_think_tags(text: str, in_think: bool) -> tuple[str, str, bool]:
    """Split a stream chunk into (main_content, reasoning_content, new_in_think_state).

    Handles <think>...</think> XML tags that DeepSeek R1 / Qwen3 models embed in content.
    Tags may span multiple chunks; in_think tracks state across calls.
    """
    main: list[str] = []
    think: list[str] = []
    i = 0
    while i < len(text):
        if not in_think:
            idx = text.find("<think>", i)
            if idx == -1:
                main.append(text[i:])
                break
            main.append(text[i:idx])
            in_think = True
            i = idx + 7  # len("<think>")
        else:
            idx = text.find("</think>", i)
            if idx == -1:
                think.append(text[i:])
                break
            think.append(text[i:idx])
            in_think = False
            i = idx + 8  # len("</think>")
    return "".join(main), "".join(think), in_think


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
        try:
            from utils.logger import workflow_event as _wfe
            _role_to_node = {
                "AMBASSADOR": "ambassador",
                "LEADER_MEDIUM": "leader_generate",
                "LEADER_LOW": "leader_generate",
                "LEADER_HIGH": "leader_generate",
            }
            _node = _role_to_node.get(str(self.registry_role_key or "").upper())
            if _node:
                _wfe(_node, "usage", f"model={target_model} prompt_tokens={prompt_tok} completion_tokens={completion_tok}")
        except Exception:
            pass

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
        _in_think = False   # state for <think> XML tag parsing across chunks
        _had_reasoning = False  # True once any reasoning content was seen

        # Import session module once; guard against unavailability (tests, etc.)
        _ws = None
        try:
            from core.runtime import session as _ws_mod
            _ws = _ws_mod
        except LookupError:
            pass

        if _ws:
            try:
                _ws.reset_stream_token_counters()
            except Exception:
                pass

        for chunk in stream:
            u = getattr(chunk, "usage", None)
            if u:
                new_pt = int(getattr(u, "prompt_tokens", 0) or 0)
                new_ct = int(getattr(u, "completion_tokens", 0) or 0)
                if new_pt > usage_prompt:
                    usage_prompt = new_pt
                    if _ws:
                        try:
                            _ws.set_stream_prompt_tokens(new_pt)
                        except Exception:
                            pass
                if new_ct > usage_completion:
                    usage_completion = new_ct
                    if _ws:
                        try:
                            _ws.set_stream_completion_tokens(new_ct)
                        except Exception:
                            pass
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # Native reasoning_content field (OpenRouter thinking models: deepseek-r1, etc.)
            reasoning_native = getattr(delta, "reasoning_content", None) or ""
            if reasoning_native and _ws:
                _had_reasoning = True
                try:
                    if not _ws.is_reasoning_active():
                        _ws.set_reasoning_active(True)
                    _ws.append_reasoning_chunk(reasoning_native)
                except Exception:
                    logger.debug("[%s] reasoning_content routing failed", self.agent_name)

            content_delta = getattr(delta, "content", None) or ""
            if not content_delta:
                continue

            # Parse <think> XML tags embedded in content stream (DeepSeek R1 / Qwen3 style)
            main_text, think_text, _in_think = _parse_think_tags(content_delta, _in_think)

            if think_text and _ws:
                _had_reasoning = True
                try:
                    if not _ws.is_reasoning_active():
                        _ws.set_reasoning_active(True)
                    _ws.append_reasoning_chunk(think_text)
                except Exception:
                    logger.debug("[%s] think-tag routing failed", self.agent_name)

            if main_text:
                # First main content after reasoning signals thinking is done
                if _had_reasoning and _ws:
                    try:
                        if _ws.is_reasoning_active():
                            _ws.set_reasoning_active(False)
                    except Exception:
                        pass
                    _had_reasoning = False

                parts.append(main_text)
                if _ws:
                    try:
                        _ws.increment_stream_char_count(len(main_text))
                    except Exception:
                        pass
                if self._stream_chunk_callback is not None:
                    try:
                        self._stream_chunk_callback(main_text)
                    except Exception as _cb_err:
                        logger.debug("[%s] Stream callback error: %s", self.agent_name, type(_cb_err).__name__)
                elif _ws:
                    try:
                        _ws.append_leader_stream_chunk(main_text)
                    except LookupError:
                        logger.debug("[%s] stream monitor not active, chunk dropped", self.agent_name)

        # Ensure reasoning is closed at end of stream
        if _had_reasoning and _ws:
            try:
                _ws.set_reasoning_active(False)
            except Exception:
                pass

        full_content = "".join(parts).strip()

        # Detect clarification request from leader:
        #   [CLARIFICATION]{"question": "...", "options": [...]}[/CLARIFICATION]
        self._last_clarif_answer: Optional[str] = None
        if _ws and "[CLARIFICATION]" in full_content:
            import re as _re, json as _json, time as _time
            _clarif_re = _re.compile(
                r'\[CLARIFICATION\]\s*(\{.*?\})\s*\[/CLARIFICATION\]',
                _re.DOTALL,
            )
            for _m in _clarif_re.finditer(full_content):
                try:
                    _cdata = _json.loads(_m.group(1))
                    _q     = _cdata.get("question", "")
                    _opts  = _cdata.get("options", [])
                    if _q and _opts:
                        _ws.set_clarification(_q, _opts)
                        logger.info("[%s] clarification triggered: %s", self.agent_name, _q[:60])
                        _deadline = _time.time() + 600
                        while _ws.is_clarification_pending() and _time.time() < _deadline:
                            _time.sleep(0.5)
                        self._last_clarif_answer = _ws.get_clarification_answer() or "__skip__"
                        _ws.clear_clarification()
                        break
                except Exception as _ce:
                    logger.debug("[%s] clarification parse error: %s", self.agent_name, _ce)
            # Strip all [CLARIFICATION] blocks from content so they don't land in context.md
            full_content = _re.sub(
                r'\[CLARIFICATION\].*?\[/CLARIFICATION\]', '', full_content, flags=_re.DOTALL
            ).strip()

        return full_content, usage_prompt, usage_completion

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

            except Exception as e:
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
                    logger.warning("[%s] Network error — retry %d/%d in %.1fs: %s", self.agent_name, attempt + 1, _MAX_RETRIES, wait, type(e).__name__)
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

        # Estimate prompt tokens for UI feedback before OpenRouter sends the final usage chunk
        try:
            from core.runtime import session as _ws_mod
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
        _clarif_rounds = 0
        attempt = 0
        while attempt < _MAX_RETRIES:
            try:
                stream = chat_completions_create_stream(
                    self.client,
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    reasoning=_reasoning_cfg,
                )
                content, usage_prompt, usage_completion = self._aggregate_stream(stream)
                _total_prompt_tok += usage_prompt
                _total_completion_tok += usage_completion

                # Clarification re-call: leader asked a question instead of generating content
                _clarif = getattr(self, '_last_clarif_answer', None)
                if _clarif is not None and not content and _clarif_rounds < 2:
                    _clarif_rounds += 1
                    if _clarif != "__skip__":
                        messages.append({"role": "assistant", "content": "[clarification requested]"})
                        messages.append({"role": "user", "content": f"User clarification: {_clarif}\n\nNow generate the full context.md."})
                    else:
                        messages.append({"role": "user", "content": "Clarification skipped. Proceed with best assumptions and generate the full context.md now."})
                    logger.info("[%s] clarification answered (%s) — re-calling for context.md", self.agent_name, _clarif[:40] if _clarif else "skip")
                    continue  # don't increment attempt

                if not content:
                    last_error = ValueError("stream returned empty content")
                    time.sleep(2 ** attempt)
                    attempt += 1
                    continue

                self.history.append({"role": "user", "content": user_prompt})
                self.history.append({"role": "assistant", "content": content})
                if _total_prompt_tok or _total_completion_tok:
                    cost = self._compute_call_cost(_total_prompt_tok, _total_completion_tok, model)
                    self._budget.session_cost += cost
                    self._budget.session_calls += 1
                    self._log_api_usage(_total_prompt_tok, _total_completion_tok, cost, model, "chat.completions.stream")
                logger.info("[%s] stream done, len=%d", self.agent_name, len(content))
                return content
            except Exception as e:
                last_error = e
                err = str(e).lower()
                if "429" in err or "rate limit" in err:
                    wait = _BASE_BACKOFF * (2 ** attempt)
                    logger.warning("[%s] stream rate limit — wait %.1fs", self.agent_name, wait)
                    time.sleep(wait)
                    attempt += 1
                    continue
                # Transient network/protocol errors — retry indefinitely with backoff
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
                    logger.warning("[%s] network error (attempt %d) — retry in %.1fs: %s",
                                   self.agent_name, attempt + 1, wait, type(e).__name__)
                    time.sleep(wait)
                    attempt += 1
                    continue
                logger.error("[%s] stream API error: %s — %s", self.agent_name, type(e).__name__, e)
                raise
        if last_error:
            raise last_error
        raise RuntimeError("stream exhausted retries")
