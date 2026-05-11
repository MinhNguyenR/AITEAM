from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "GENERAL_RESEARCHER": {
        "model": "x-ai/grok-4.1-fast",
        "role": "Researcher",
        "reason": "Tổng hợp thông tin và cung cấp bối cảnh cho dự án.",
        "tier": "RESEARCH",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
        "reasoning": {"effort": "high", "exclude": False},
    },
    "TECHNICAL_RESEARCHER": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Tech Researcher",
        "reason": "Nghiên cứu tài liệu kỹ thuật và các thư viện chuyên sâu.",
        "tier": "RESEARCH",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
        "reasoning": {"effort": "high", "exclude": False},
    },
    "EXPERT": {
        "model": "google/gemini-3.1-pro-preview",
        "role": "Expert",
        "reason": "Handles expert-level planning, deep validation, and high-complexity technical reasoning.",
        "tier": "SPECIALIST",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
}
