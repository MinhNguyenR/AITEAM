"""Persist LLM usage rows to local tracker (dashboard source of truth)."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


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
