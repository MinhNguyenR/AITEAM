"""Static translation catalog - fallback strings for all supported languages."""
from __future__ import annotations

from .catalog_vi import VI_STRINGS
from .catalog_en import EN_STRINGS

DEFAULT_STRINGS: dict[str, dict[str, str]] = {
    "vi": VI_STRINGS,
    "en": EN_STRINGS,
}

__all__ = ["DEFAULT_STRINGS"]
