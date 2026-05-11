"""Low-level OpenRouter transport helpers: client factory, completions wrappers, token utils."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


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
    extra_headers: Optional[Dict[str, str]] = None,
):
    kwargs: Dict[str, Any] = dict(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
    )
    if extra_headers:
        kwargs["extra_headers"] = extra_headers
    return client.chat.completions.create(**kwargs)


def chat_completions_create_stream(
    client: Any,
    *,
    model: str,
    messages: List[Dict[str, Any]],
    max_tokens: int,
    temperature: float,
    reasoning: Optional[Dict] = None,
    extra_headers: Optional[Dict[str, str]] = None,
):
    kwargs: Dict[str, Any] = dict(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
        stream_options={"include_usage": True},
    )
    extra: Dict[str, Any] = {"provider": {"require_parameters": True, "data_collection": "deny"}}
    if reasoning:
        extra["reasoning"] = reasoning
    kwargs["extra_body"] = extra
    if extra_headers:
        kwargs["extra_headers"] = extra_headers
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


def _extract_cache_tokens(usage: Any) -> tuple[int, int]:
    """Return (cache_read_tokens, cache_write_tokens) from an API usage object."""
    cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
    cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)
    if not cache_read:
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            if isinstance(details, dict):
                cache_read = int(details.get("cached_tokens", 0) or 0)
            else:
                cache_read = int(getattr(details, "cached_tokens", 0) or 0)
    return cache_read, cache_write


def log_usage_event(payload: Dict[str, Any]) -> None:
    try:
        from utils.tracker import append_usage_log
        append_usage_log(payload)
    except (OSError, ValueError) as e:
        logger.debug("Usage log skipped: %s", e)
