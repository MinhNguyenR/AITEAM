from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "SECRETARY": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "CLI Executor",
        "reason": "Thực thi lệnh terminal, quản lý file và tự động hóa tác vụ hệ thống.",
        "tier": "SUPPORT",
        "priority": 2,
        "max_tokens": 2048,
        "temperature": 0.1,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "TOOL_CURATOR": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Tool Manager",
        "reason": "Quản lý thư viện, package, dependency và đề xuất công cụ phù hợp cho task.",
        "tier": "SUPPORT",
        "priority": 1,
        "max_tokens": 4096,
        "temperature": 0.2,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "BROWSER": {
        "model": "perplexity/sonar",
        "role": "Browser",
        "reason": "Tìm kiếm web real-time, truy xuất tài liệu và xác minh thông tin từ nguồn bên ngoài.",
        "tier": "SUPPORT",
        "priority": 2,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "EXPLAINER": {
        "model": "nvidia/nemotron-3-super-120b-a12b",
        "role": "AI Explainer",
        "reason": "Chuyên giải thích các 'trade-offs' thiết kế và giải thích các kết quả của mô hình AI.",
        "tier": "WORKER",
        "priority": 3,
        "max_tokens": 4096,
        "temperature": 0.2,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
}
