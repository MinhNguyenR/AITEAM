"""Chat agent — inline assistant for workflow TUI and ask mode.

Uses CHAT_MODEL_STANDARD (google/gemini-2.5-flash-lite) from registry.
System prompt covers: workflow pipeline, all roles, all CLI commands.
"""
from __future__ import annotations

from typing import Optional

from core.config import config as _config
from core.config.settings import openrouter_base_url
from core.domain.prompts import ASK_MODE_SYSTEM_PROMPT


class ChatAgent:
    """Inline chat assistant — reads CHAT_MODEL_STANDARD from registry."""

    def __init__(self, mode: str = "standard") -> None:
        worker_id = "CHAT_MODEL_THINKING" if mode == "thinking" else "CHAT_MODEL_STANDARD"
        cfg = _config.get_worker(worker_id) or {}
        self.model       = str(cfg.get("model") or _config.ASK_CHAT_STANDARD_MODEL)
        self.max_tokens  = int(cfg.get("max_tokens") or 3000)
        self.temperature = float(cfg.get("temperature") if cfg.get("temperature") is not None else 1.2)
        self.top_p       = float(cfg.get("top_p")       if cfg.get("top_p")       is not None else 0.95)

    def ask(
        self,
        question: str,
        history: Optional[list] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call the model. history = list of {role, content} dicts (no system entry)."""
        from openai import OpenAI

        sys_content = system_prompt or ASK_MODE_SYSTEM_PROMPT
        messages: list[dict] = [{"role": "system", "content": sys_content}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        client = OpenAI(api_key=_config.api_key, base_url=openrouter_base_url())
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
        )
        return (resp.choices[0].message.content or "").strip()
