from __future__ import annotations

from typing import Any, Callable, List, Tuple

from prompt_toolkit.layout.containers import ConditionalContainer, Float, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame

from core.cli.python_cli.i18n import t

from .items import (
    POPUP_WIDTH,
    ptk_frame_style,
    ptk_popup_window_style,
    render_popup_text,
)



def make_command_palette_body(
    *,
    get_query: Callable[[], str],
    get_items: Callable[[], List[Tuple[str, str]]],
    width: int = POPUP_WIDTH,
    frame_cls: type = Frame,
) -> Frame:
    """Return a bare Frame widget (no Float wrapper) for inline embedding in an HSplit."""

    def _body_text():
        return render_popup_text(get_query(), get_items())

    body = Window(
        content=FormattedTextControl(_body_text),
        style=ptk_popup_window_style(),
        dont_extend_height=True,
    )
    return frame_cls(
        body=body,
        title=t("ui.commands"),
        style=ptk_frame_style(),
        width=width,
    )


def make_command_palette_float(
    *,
    get_query: Callable[[], str],
    get_items: Callable[[], List[Tuple[str, str]]],
    show_filter: Any,
    width: int = POPUP_WIDTH,
    frame_cls: type = Frame,
    float_kwargs: dict[str, Any] | None = None,
) -> Float:
    """Shared Float + Frame + popup body; callers supply query/items/filter and Float position."""
    fk = dict(float_kwargs or {})

    def _body_text():
        return render_popup_text(get_query(), get_items())

    from prompt_toolkit.layout.dimension import D
    from prompt_toolkit.layout.margins import ScrollbarMargin
    from prompt_toolkit.layout.containers import VSplit

    body_win = Window(
        content=FormattedTextControl(_body_text),
        style=ptk_popup_window_style(),
        dont_extend_height=True,
        height=D(max=15),
        right_margins=[ScrollbarMargin(display_arrows=True)],
    )
    framed = frame_cls(
        body=body_win,
        title=t("ui.commands"),
        style=ptk_frame_style(),
        width=width,
    )
    return Float(
        content=ConditionalContainer(content=framed, filter=show_filter),
        **fk,
    )
