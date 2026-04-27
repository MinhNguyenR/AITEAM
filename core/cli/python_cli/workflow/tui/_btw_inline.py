"""Shared logic for inline /btw streaming in workflow TUIs (list_view + monitor_app).

Resolves leader model from registry, opens OpenRouter stream, yields text chunks.
Caller drives all rendering — this module is render-agnostic.
"""

from __future__ import annotations

import logging
from typing import Any, Iterator, Optional, Tuple

logger = logging.getLogger(__name__)


def resolve_btw_model_settings(
    active: str,
    tier: Optional[str],
    *,
    fallback_role_key: str = "LEADER_MEDIUM",
) -> Tuple[str, int, float]:
    """Return (model_id, max_tokens, temperature) for active step's leader."""
    from core.config import config as _cfg

    model: str = ""
    max_tokens: int = 1200
    temperature: float = 0.7
    try:
        from .monitor_helpers import _registry_key_for_step

        key = _registry_key_for_step(active, tier)
        wcfg = _cfg.get_worker(key or fallback_role_key) or {}
        model = str(wcfg.get("model") or "")
        max_tokens = int(wcfg.get("max_tokens") or 1200)
        temperature = float(wcfg.get("temperature") or 0.7)
    except Exception:
        logger.debug("[btw_inline] could not resolve registry key for step", exc_info=True)
    if not model:
        model = str(
            getattr(_cfg, "ASK_CHAT_STANDARD_MODEL", "openai/gpt-4o-mini") or ""
        )
    return model, max_tokens, temperature


def stream_btw_response(
    *,
    active: str,
    tier: Optional[str],
    role_name: str,
    note: str,
    user_prefix: str = "BTW note (full)",
) -> Iterator[str]:
    """Open the OpenRouter stream for an inline /btw note and yield text chunks.

    Caller handles all rendering. Raises on fatal errors (network, auth, etc).
    """
    from agents._api_client import make_openai_client
    from core.config import config as _cfg
    from core.config.settings import openrouter_base_url

    model, max_tokens, temperature = resolve_btw_model_settings(active, tier)

    system_prompt = (
        f"Bạn là {role_name} AI trong pipeline. "
        f"User vừa gửi ghi chú (btw) trong lúc bạn đang làm việc.\n"
        f"Đọc ghi chú và phản hồi ngắn gọn, thiết thực."
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"{user_prefix}: {note}"},
    ]

    client = make_openai_client(_cfg.api_key, openrouter_base_url())
    stream: Any = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        text = (getattr(delta, "content", None) or "") if delta else ""
        if text:
            yield text


__all__ = ["resolve_btw_model_settings", "stream_btw_response"]
