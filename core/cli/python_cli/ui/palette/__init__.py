"""Slash command palette UI — single package under ui/palette/."""
from __future__ import annotations

from .app import ask_with_palette
from .footer import markup_to_ansi, palette_footer_markup
from .items import POPUP_WIDTH, build_popup_items, build_popup_items_all, render_popup_text
from .lexer import CommandLexer
from .popup import make_command_palette_float
from .shared import (
    COMMAND_PALETTE_CONTEXT_MONITOR,
    CommandPaletteFrame,
    command_palette_float_attached,
    command_palette_inline_body,
    palette_application_color_depth,
    palette_application_style,
    palette_autocomplete_snapshot,
    palette_buffer_input_center,
    palette_float_kwargs,
    palette_gutter_input_row,
    palette_popup_show_condition,
)

_POPUP_WIDTH = POPUP_WIDTH

__all__ = [
    "COMMAND_PALETTE_CONTEXT_MONITOR",
    "CommandLexer",
    "CommandPaletteFrame",
    "POPUP_WIDTH",
    "_POPUP_WIDTH",
    "ask_with_palette",
    "build_popup_items",
    "build_popup_items_all",
    "command_palette_float_attached",
    "command_palette_inline_body",
    "make_command_palette_float",
    "markup_to_ansi",
    "palette_application_color_depth",
    "palette_application_style",
    "palette_autocomplete_snapshot",
    "palette_buffer_input_center",
    "palette_float_kwargs",
    "palette_footer_markup",
    "palette_gutter_input_row",
    "palette_popup_show_condition",
    "render_popup_text",
]
