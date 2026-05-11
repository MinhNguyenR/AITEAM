"""Translation loader — reads .translations.json and merges with catalog fallback."""
from __future__ import annotations
import json
import os

from .catalog import DEFAULT_STRINGS

_FALLBACK_LANG = "vi"
_TRANS_FILE = os.path.join(os.path.dirname(__file__), "..", "ui", ".translations.json")


def _load_strings() -> dict:
    if not os.path.exists(_TRANS_FILE):
        try:
            os.makedirs(os.path.dirname(_TRANS_FILE), exist_ok=True)
            with open(_TRANS_FILE, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_STRINGS, f, ensure_ascii=False, indent=4)
        except Exception:
            return DEFAULT_STRINGS
    try:
        with open(_TRANS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if _FALLBACK_LANG in data:
                return data
    except Exception:
        pass
    return DEFAULT_STRINGS


STRINGS = _load_strings()

__all__ = ["STRINGS", "_FALLBACK_LANG", "_load_strings"]
