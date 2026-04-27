from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "LEADER_LOW": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "Lead Low",
        "reason": "Dẫn dắt nhóm xử lý task đơn giản, tốc độ cao, chi phí thấp.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
    },
    "LEADER_MEDIUM": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Lead Medium",
        "reason": "Dẫn dắt nhóm xử lý task trung bình, cân bằng giữa chất lượng và tốc độ.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
    },
    "LEADER_HIGH": {
        "model": "google/gemini-3.1-pro-preview",
        "role": "Lead High",
        "reason": "Dẫn dắt nhóm xử lý task phức tạp, ưu tiên chất lượng và độ chính xác cao.",
        "tier": "LEAD",
        "priority": 1,
        "max_tokens": 8192,
        "temperature": 0.6,
        "top_p": 1.0,
    },
}
