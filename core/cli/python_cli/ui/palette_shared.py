"""Shim: palette lives in core.cli.python_cli.ui.palette."""
from __future__ import annotations

from core.cli.python_cli.ui.palette import (
    POPUP_WIDTH as _POPUP_WIDTH,
    CommandLexer,
    build_popup_items,
    build_popup_items_all,
    markup_to_ansi,
    palette_footer_markup,
    render_popup_text,
)

_POPUP_WIDTH = _POPUP_WIDTH

__all__ = [
    "CommandLexer",
    "_POPUP_WIDTH",
    "build_popup_items",
    "build_popup_items_all",
    "markup_to_ansi",
    "palette_footer_markup",
    "render_popup_text",
]
