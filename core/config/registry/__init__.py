from __future__ import annotations

from typing import Any, Dict, Optional

from .coding import REGISTRY as _CODING

MODEL_REGISTRY: Dict[str, Dict[str, Any]] = {**_CODING}

TIER_MODEL_MAP = {
    "LOW": "xiaomi/mimo-v2-flash",
    "MEDIUM": "xiaomi/mimo-v2-flash",
    "EXPERT": "moonshotai/kimi-k2.6",
    "HARD": "google/gemini-3.1-pro-preview",
}

ASK_CHAT_STANDARD_MODEL = MODEL_REGISTRY["CHAT_MODEL_STANDARD"]["model"]
ASK_CHAT_THINKING_MODEL = MODEL_REGISTRY["CHAT_MODEL_THINKING"]["model"]


def get_worker_config(worker_id: str) -> Optional[Dict[str, Any]]:
    return MODEL_REGISTRY.get(worker_id.upper())


def get_model_for_tier(tier: str) -> str:
    return TIER_MODEL_MAP.get(tier.upper(), TIER_MODEL_MAP["MEDIUM"])


__all__ = [
    "MODEL_REGISTRY",
    "TIER_MODEL_MAP",
    "ASK_CHAT_STANDARD_MODEL",
    "ASK_CHAT_THINKING_MODEL",
    "get_worker_config",
    "get_model_for_tier",
]
