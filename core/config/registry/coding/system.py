from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "AMBASSADOR": {
        "model": "openai/gpt-5.4-nano",
        "role": "Ambassador",
        "reason": "Phân tích task của user, phân loại tier và chọn model phù hợp để xử lý.",
        "tier": "AMBASSADOR",
        "priority": 0,
        "max_tokens": 300,
        "temperature": 0.1,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "COMMANDER": {
        "model": "anthropic/claude-opus-4.6",
        "role": "Commander",
        "reason": "Điều phối toàn bộ agent pipeline, phân bổ tài nguyên và ra quyết định chiến lược.",
        "tier": "COMMAND",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.3,
        "top_p": 1.0,
        "reasoning": {"effort": "high", "exclude": False},
    },
    "COMPACT_WORKER": {
        "model": "x-ai/grok-4.1-fast",
        "role": "Compact",
        "reason": "Xử lý context window cực lớn, tóm tắt và nén thông tin cho các pipeline dài.",
        "tier": "COMPACT",
        "priority": 0,
        "max_tokens": 252000,
        "temperature": 0.6,
        "top_p": 0.95,
        "reasoning": {"effort": "medium", "exclude": False},
    },
}
