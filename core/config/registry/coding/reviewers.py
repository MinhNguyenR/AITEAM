from __future__ import annotations


from typing import Any, Dict


REGISTRY: Dict[str, Dict[str, Any]] = {
    "FAST_REVIEWER": {
        "model": "xiaomi/mimo-v2-flash",
        "role": "FastReviewer",
        "reason": "Review code nhanh, táº­p trung logic hiá»‡n táº¡i và phát hiá»‡n bug rÃµ ràng.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 4096,
        "temperature": 0.1,
        "top_p": 1.0,
        "mode": {
            "standard": "Review bÃ¬nh thÆ°á»ng, táº­p trung cháº¥t lÆ°á»£ng thay Ä‘á»•i hiá»‡n táº¡i.",
            "reflection": "Suy ngáº«m láº¡i lá»—i sai, Ä‘á»•i hÆ°á»›ng tÆ° duy, rút kinh nghiá»‡m rá»“i review láº¡i.",
        },
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "REVIEWER": {
        "model": "deepseek/deepseek-v4-flash",
        "role": "Reviewer",
        "reason": "Review sâu vá» technical debt, maintainability và các váº¥n Ä‘á» kiáº¿n trúc dài háº¡n.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 8192,
        "temperature": 0.1,
        "top_p": 1.0,
        "mode": {
            "standard": "Review bÃ¬nh thÆ°á»ng, táº­p trung technical debt và maintainability.",
            "reflection": "Suy ngáº«m láº¡i các lá»—i sai cÃ²n sÃ³t, pháº£n biá»‡n láº¡i giáº£ Ä‘á»‹nh, rá»“i review láº¡i.",
        },
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "ADVANCED_REVIEWER_A": {
        "model": "deepseek/deepseek-v4-pro",
        "role": "Advanced Reviewer A",
        "reason": "Review sâu vá» technical debt, maintainability và các váº¥n Ä‘á» kiáº¿n trúc dài háº¡n.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 8192,
        "temperature": 0.1,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
    "ADVANCED_REVIEWER_B": {
        "model": "x-ai/grok-4.3",
        "role": "Advanced Reviewer B",
        "reason": "Review sâu vá» technical debt, maintainability và các váº¥n Ä‘á» kiáº¿n trúc dài háº¡n.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 8192,
        "temperature": 0.1,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
        "ADVANCED_REVIEWER_C": {
        "model": "xiaomi/mimo-v2.5-pro",
        "role": "Advanced Reviewer C",
        "reason": "Review sâu vá» technical debt, maintainability và các váº¥n Ä‘á» kiáº¿n trúc dài háº¡n.",
        "tier": "REVIEW",
        "priority": 2,
        "max_tokens": 8192,
        "temperature": 0.1,
        "top_p": 1.0,
        "reasoning": {"effort": "medium", "exclude": False},
    },
}
