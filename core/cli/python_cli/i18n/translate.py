"""t() — locale-aware string lookup with vi fallback."""
from __future__ import annotations

from .catalog import DEFAULT_STRINGS
from .loader import STRINGS, _FALLBACK_LANG


def t(key: str) -> str:
    """Return localized string for key based on display_language setting."""
    try:
        from core.app_state import get_cli_settings
        lang = str(get_cli_settings().get("display_language") or _FALLBACK_LANG)
    except Exception:
        lang = _FALLBACK_LANG
    bucket = STRINGS.get(lang) or STRINGS[_FALLBACK_LANG]
    return bucket.get(key) or DEFAULT_STRINGS[_FALLBACK_LANG].get(key, key)


__all__ = ["t"]
