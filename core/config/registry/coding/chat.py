from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "CHAT_MODEL_STANDARD": {
        "model": "google/gemini-2.5-flash-lite",
        "role": "Chat",
        "reason": "Trả lời câu hỏi nhanh, giải thích khái niệm và hỗ trợ chat thông thường.",
        "tier": "CHAT",
        "priority": 0,
        "max_tokens": 3000,
        "temperature": 1.2,
        "top_p": 0.95,
    },
    "CHAT_MODEL_THINKING": {
        "model": "google/gemini-2.5-flash-lite:exacto",
        "role": "Chat (Thinking)",
        "reason": "Chat chuyên sâu với khả năng suy luận chuỗi bước trước khi trả lời.",
        "tier": "CHAT",
        "priority": 0,
        "max_tokens": 4000,
        "temperature": 1.2,
        "top_p": 0.95,
    },
}
