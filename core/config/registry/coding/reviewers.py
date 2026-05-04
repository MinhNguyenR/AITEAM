from __future__ import annotations

from typing import Any, Dict

REGISTRY: Dict[str, Dict[str, Any]] = {
    "FAST_REVIEWER": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "FastReviewer",
        "reason": "Review code nhanh, tập trung logic hiện tại và phát hiện bug rõ ràng.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
        "mode": {
            "standard": "Review bình thường, tập trung chất lượng thay đổi hiện tại.",
            "reflection": "Suy ngẫm lại lỗi sai, đổi hướng tư duy, rút kinh nghiệm rồi review lại.",
        },
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "REVIEWER": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Reviewer",
        "reason": "Review sâu về technical debt, maintainability và các vấn đề kiến trúc dài hạn.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 8192,
        "temperature": 0.1,
        "top_p": 1.0,
        "mode": {
            "standard": "Review bình thường, tập trung technical debt và maintainability.",
            "reflection": "Suy ngẫm lại các lỗi sai còn sót, phản biện lại giả định, rồi review lại.",
        },
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "FINAL_REVIEWER": {
        "model": "moonshotai/kimi-k2.6",
        "role": "Final Reviewer",
        "reason": "Kiểm tra lần cuối toàn bộ output trước khi giao, đảm bảo chất lượng end-to-end.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 8192,
        "temperature": 0.1,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
}
