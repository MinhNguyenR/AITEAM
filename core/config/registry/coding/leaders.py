from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "LEADER_LOW": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "Lead Low",
        "reason": "Dẫn dắt các tác vụ cơ bản, xử lý nhanh với chi phí tối ưu.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 32768,
        "temperature": 0.6,
        "top_p": 1.0,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "reasoning": {"effort": "high", "enabled": True, "exclude": False, "verbosity": "high"},
    },
    "LEADER_MEDIUM": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Lead Medium",
        "reason": "Thiết kế kiến trúc hệ thống và điều phối các luồng logic phức tạp.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 16384,
        "temperature": 0.2,
        "top_p": 1.0,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "reasoning": {"effort": "high", "enabled": True, "exclude": False, "verbosity": "high"},
    },
    "LEADER_HIGH": {
        "model": "x-ai/grok-4.3",
        "role": "Lead Hard",
        "reason": "Lập kế hoạch chiến lược và điều hành các dự án kỹ thuật chuyên sâu.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 16384,
        "temperature": 0.2,
        "top_p": 1.0,
        "cache_enabled": True,
        "cache_ttl_seconds": 300,
        "reasoning": {"effort": "high", "enabled": True, "exclude": False, "verbosity": "high"},
    },
}
