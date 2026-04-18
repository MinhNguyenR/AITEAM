"""OpenRouter wallet API."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict

import requests

logger = logging.getLogger(__name__)

OPENROUTER_API = "https://openrouter.ai/api/v1"


def _auth_header() -> dict:
    key = os.getenv("OPENROUTER_API_KEY", "")
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def fetch_wallet() -> Dict[str, Any]:
    try:
        r = requests.get(f"{OPENROUTER_API}/credits", headers=_auth_header(), timeout=8)
        r.raise_for_status()
        data = r.json()
        d = data.get("data", data)
        total = float(d.get("total_credits", 0.0) or 0.0)
        used = float(d.get("usage", 0.0) or 0.0)
        return {
            "ok": True,
            "total_credits": total,
            "remaining_credits": total - used,
            "currency": "USD",
        }
    except (requests.RequestException, ValueError, TypeError, KeyError) as e:
        logger.warning("[Tracker] fetch_wallet failed: %s", e)
        return {"ok": False, "error": str(e), "total_credits": 0.0, "remaining_credits": 0.0, "currency": "USD"}
