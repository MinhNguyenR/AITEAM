from __future__ import annotations

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import ConditionalContainer, FloatContainer, HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.dimension import Dimension as D
from .footer import markup_to_ansi
from .items import POPUP_WIDTH
from .shared import (
    command_palette_float_attached,
    palette_application_color_depth,
    palette_application_style,
    palette_autocomplete_snapshot,
    palette_gutter_input_row,
    palette_popup_show_condition,
)


def ask_with_palette(
    prompt: str,
    context: str = "main",
    default: str = "",
    gate_pending: bool = False,
    header_ansi: str | None = None,
) -> str:
    state: dict = {
        "autocomplete_active": False,
        "autocomplete_items": [],
        "result": None,
    }

    def _accept_handler(buff):
        state["result"] = buff.text
        app.exit(result=buff.text)

    main_buffer = Buffer(multiline=False, accept_handler=_accept_handler)

    def _invalidate():
        try:
            from prompt_toolkit.application import get_app

            get_app().invalidate()
        except Exception:
            pass

    def _on_text_changed(_buff):
        items, active = palette_autocomplete_snapshot(
            main_buffer.text,
            context=context,
            gate_pending=gate_pending,
        )
        state["autocomplete_items"] = items
        state["autocomplete_active"] = active
        _invalidate()

    main_buffer.on_text_changed += _on_text_changed

    kb = KeyBindings()

    @kb.add("c-c")
    @kb.add("escape")
    def _cancel(event):
        event.app.exit(result="")

    @kb.add("tab")
    def _tab_complete(event):
        """Complete input with the first suggested command."""
        items = state["autocomplete_items"]
        first = next((c for c, _ in items if c != "__sep__"), None)
        if first:
            from prompt_toolkit.document import Document
            main_buffer.set_document(
                Document(first, cursor_position=len(first)),
                bypass_readonly=True,
            )
            # Re-evaluate autocomplete so popup updates immediately
            _on_text_changed(main_buffer)
            event.app.invalidate()

    def _get_term_width() -> int:
        try:
            from prompt_toolkit.application import get_app
            return get_app().output.get_size().columns
        except Exception:
            return 120

    def _aiteam_sep_text():
        w = _get_term_width()
        # prefix "──── aiteam " is 12 visible chars; fill the rest to w
        right = "─" * max(0, w - 12)
        mk = f"[dim]──── [bold]aiteam[/bold] {right}[/dim]"
        return to_formatted_text(ANSI(markup_to_ansi(mk, width=w)))

    def _bottom_sep_text():
        w = _get_term_width()
        return to_formatted_text(ANSI(markup_to_ansi(f"[dim]{'─' * w}[/dim]", width=w)))

    sep_window = Window(
        content=FormattedTextControl(_aiteam_sep_text, focusable=False),
        height=1,
        dont_extend_height=True,
    )
    bottom_sep_window = Window(
        content=FormattedTextControl(_bottom_sep_text, focusable=False),
        height=1,
        dont_extend_height=True,
    )

    input_row, _attach_win = palette_gutter_input_row(
        buffer=main_buffer, before_input=prompt
    )
    _show_popup = palette_popup_show_condition(lambda: state["autocomplete_active"])

    if header_ansi:
        # Full-screen mode (main menu): Float overlay above the fill area.
        _header_ansi = header_ansi
        _fill = Window(
            content=FormattedTextControl(
                lambda: to_formatted_text(ANSI(_header_ansi)),
                focusable=False,
            ),
            height=D(weight=1),
        )
        popup_float = command_palette_float_attached(
            get_query=lambda: main_buffer.text,
            get_items=lambda: state["autocomplete_items"],
            show_filter=_show_popup,
            width=POPUP_WIDTH,
            attach_to_window=_attach_win,
        )
        body = HSplit([_fill, sep_window, input_row, bottom_sep_window])
        layout = Layout(
            FloatContainer(content=body, floats=[popup_float]),
            focused_element=main_buffer,
        )
        _full_screen = True
    else:
        # Inline mode (sub-CLIs): ConditionalContainer above the command area.
        # In ptk inline mode the app is anchored at the terminal bottom.
        # When the popup activates the app grows UPWARD — command line stays
        # pinned at the bottom and the box appears above it, exactly like
        # the shadow-box seen in the workflow TUI.
        from .popup import make_command_palette_body
        popup_frame = make_command_palette_body(
            get_query=lambda: main_buffer.text,
            get_items=lambda: state["autocomplete_items"],
            width=POPUP_WIDTH,
        )
        popup_cc = ConditionalContainer(content=popup_frame, filter=_show_popup)
        body = HSplit([popup_cc, sep_window, input_row, bottom_sep_window])
        layout = Layout(body, focused_element=main_buffer)
        _full_screen = False

    app = Application(
        layout=layout,
        key_bindings=kb,
        style=palette_application_style(),
        full_screen=_full_screen,
        color_depth=palette_application_color_depth(),
    )

    res = app.run()
    return res or default
