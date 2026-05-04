"""Workflow monitor palette: autocomplete rules, chrome, Float, Application defaults.

Call sites (CLI ask_with_palette, monitor _layout_mixin) only wire buffers/layout;
palette behavior lives here.
"""
from __future__ import annotations

import sys
from typing import Any, Callable, List, Tuple

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.filters import Condition
from prompt_toolkit.layout.containers import VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.output.color_depth import ColorDepth
from prompt_toolkit.styles import BaseStyle, merge_styles
from prompt_toolkit.styles.defaults import default_ui_style
from prompt_toolkit.widgets import Frame as CommandPaletteFrame

from prompt_toolkit.layout.containers import ConditionalContainer

from .items import POPUP_WIDTH, build_popup_items
from .lexer import CommandLexer
from .popup import make_command_palette_body, make_command_palette_float

COMMAND_PALETTE_CONTEXT_MONITOR = "monitor"


def palette_autocomplete_snapshot(
    text: str,
    *,
    context: str,
    gate_pending: bool,
) -> tuple[list[tuple[str, str]], bool]:
    """Full palette list for slash input; visibility matches workflow monitor."""
    if not text or text[0] != "/":
        return [], False
    items = build_popup_items(query=text, context=context, gate_pending=gate_pending)
    flat = [(c, d) for c, d in items if c != "__sep__"]
    if not flat:
        return items, False
    if len(flat) == 1 and flat[0][0].lower() == text.lower():
        return items, False
    return items, True


def palette_buffer_input_center(*, buffer: Buffer, before_input: str) -> Window:
    return Window(
        content=BufferControl(
            buffer=buffer,
            input_processors=[BeforeInput(before_input)],
            lexer=CommandLexer(),
            focusable=True,
        ),
        height=D(min=1, preferred=1, max=6),
        wrap_lines=True,
        dont_extend_height=True,
    )


def palette_gutter_input_row(*, buffer: Buffer, before_input: str) -> tuple[VSplit, Window]:
    center = palette_buffer_input_center(buffer=buffer, before_input=before_input)

    def _gutter() -> Window:
        return Window(
            content=FormattedTextControl(
                lambda: [("fg:#555555", "│")],
                focusable=False,
            ),
            width=1,
        )

    row = VSplit([_gutter(), center, _gutter()])
    return row, center


def palette_popup_show_condition(
    autocomplete_active: Callable[[], bool],
    *,
    enabled_when: Callable[[], bool] | None = None,
) -> Condition:
    """Float filter: popup when active and optional extra gate (e.g. not in check mode)."""

    @Condition
    def _show() -> bool:
        if enabled_when is not None and not enabled_when():
            return False
        return bool(autocomplete_active())

    return _show


def palette_application_style() -> BaseStyle:
    return merge_styles([default_ui_style()])


def palette_application_color_depth() -> ColorDepth:
    return ColorDepth.TRUE_COLOR


def palette_float_kwargs(attach_to_window: Window) -> dict[str, Any]:
    return {
        "left": 2,
        "ycursor": True,
        "allow_cover_cursor": False,
        "attach_to_window": attach_to_window,
        "hide_when_covering_content": False,
    }


def command_palette_float_attached(
    *,
    get_query: Callable[[], str],
    get_items: Callable[[], List[Tuple[str, str]]],
    show_filter: Any,
    attach_to_window: Window,
    width: int = POPUP_WIDTH,
) -> Any:
    return make_command_palette_float(
        get_query=get_query,
        get_items=get_items,
        show_filter=show_filter,
        width=width,
        frame_cls=CommandPaletteFrame,
        float_kwargs=palette_float_kwargs(attach_to_window),
    )


def command_palette_inline_body(
    *,
    get_query: Callable[[], str],
    get_items: Callable[[], List[Tuple[str, str]]],
    show_filter: Any,
    width: int = POPUP_WIDTH,
) -> Any:
    """Return a ConditionalContainer wrapping a bare Frame, for embedding above
    the input row in an HSplit (inline / non-full-screen applications).

    When show_filter is False the container collapses to 0 rows, preserving
    the terminal state printed before the prompt_toolkit Application started.
    """
    framed = make_command_palette_body(
        get_query=get_query,
        get_items=get_items,
        width=width,
        frame_cls=CommandPaletteFrame,
    )
    return ConditionalContainer(content=framed, filter=show_filter)
