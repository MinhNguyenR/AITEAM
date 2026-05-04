from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "LEADER_LOW": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "Lead Low",
        "reason": "Dẫn dắt nhóm xử lý task đơn giản, tốc độ cao, chi phí thấp.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 32768,
        "temperature": 0.6,
        "top_p": 1.0,
        "reasoning": {"effort": "high", "exclude": False},
    },
    "LEADER_MEDIUM": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Lead Medium",
        "reason": "Dẫn dắt nhóm xử lý task trung bình, cân bằng giữa chất lượng và tốc độ.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 32768,
        "temperature": 0.6,
        "top_p": 1.0,
        "reasoning": {"effort": "high", "exclude": False},
    },
    "LEADER_HIGH": {
        "model": "moonshotai/kimi-k2.6",
        "role": "Lead High",
        "reason": "Dẫn dắt nhóm xử lý task phức tạp, ưu tiên chất lượng và độ chính xác cao.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 32768,
        "temperature": 0.6,
        "top_p": 1.0,
        "reasoning": {"effort": "high", "exclude": False},
    },
}
