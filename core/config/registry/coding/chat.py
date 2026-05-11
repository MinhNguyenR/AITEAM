from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "CHAT_MODEL_STANDARD": {
        "model": "google/gemini-2.5-flash-lite",
        "role": "Chat",
        "reason": "Hỗ trợ giải đáp thắc mắc và trao đổi thông tin thông thường.",
        "tier": "CHAT",
        "priority": 0,
        "max_tokens": 3000,
        "temperature": 1.2,
        "top_p": 0.95,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "CHAT_MODEL_THINKING": {
        "model": "google/gemini-2.5-flash-lite",
        "role": "Chat (Thinking)",
        "reason": "Trao đổi chuyên sâu với khả năng suy luận đa bước.",
        "tier": "CHAT",
        "priority": 0,
        "max_tokens": 12000,
        "temperature": 1.2,
        "top_p": 0.95,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "reasoning": {"effort": "high", "exclude": False},
    },
}
