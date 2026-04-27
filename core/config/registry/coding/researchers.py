from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "GENERAL_RESEARCHER": {
        "model": "x-ai/grok-4.1-fast",
        "role": "Researcher",
        "reason": "Tổng hợp thông tin đa nguồn, phân tích xu hướng và cung cấp bối cảnh cho pipeline.",
        "tier": "RESEARCH",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
    },
    "TECHNICAL_RESEARCHER": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Tech Researcher",
        "reason": "Nghiên cứu kỹ thuật chuyên sâu: API docs, library internals và best practices.",
        "tier": "RESEARCH",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
    },
    "EXPERT": {
        "model": "moonshotai/kimi-k2.6",
        "role": "Architect",
        "reason": "Thiết kế kiến trúc hệ thống, đưa ra quyết định công nghệ và review thiết kế tổng thể.",
        "tier": "SPECIALIST",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
    },
}
