from __future__ import annotations

import os

from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import FloatContainer, HSplit, Window, ConditionalContainer
from prompt_toolkit.layout.controls import FormattedTextControl, UIContent, UIControl
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.mouse_events import MouseEventType
from prompt_toolkit.data_structures import Point

from .footer import markup_to_ansi
from .items import POPUP_WIDTH
from .shared import (
    command_palette_float_attached,
    palette_application_color_depth,
    palette_application_style,
    palette_autocomplete_snapshot,
    palette_float_bottom,
    palette_gutter_input_row,
    palette_popup_show_condition,
    _last_token_marker,
)
from .popup import make_command_palette_body


class _ScrollableAnsiControl(UIControl):
    def __init__(self, get_ansi, scroll_state: dict[str, int]) -> None:
        self._get_ansi = get_ansi
        self._scroll_state = scroll_state
        self._cache_raw = ""
        self._cache_lines: list[list] = []

    def create_content(self, width: int, height: int) -> UIContent:
        raw = str(self._get_ansi() or " ")
        if raw != self._cache_raw:
            self._cache_raw = raw
            lines: list[list] = []
            for part in raw.rstrip("\n").split("\n"):
                lines.append(to_formatted_text(ANSI(part)))
            self._cache_lines = lines or [[]]
        max_scroll = max(0, len(self._cache_lines) - 1)
        offset = max(0, min(int(self._scroll_state.get("offset", 0)), max_scroll))
        self._scroll_state["offset"] = offset
        self._scroll_state["max"] = max_scroll

        def get_line(i: int):
            return self._cache_lines[i] if 0 <= i < len(self._cache_lines) else []

        return UIContent(
            get_line=get_line,
            line_count=max(1, len(self._cache_lines)),
            cursor_position=Point(x=0, y=offset),
            show_cursor=False,
        )

    def is_focusable(self) -> bool:
        return False


def _plain_prompt(prompt: str) -> str:
    """Strip rich markup/ansi for the prompt_toolkit gutter."""
    try:
        from rich.text import Text
        # Handle potential non-string types and strip markup
        t_obj = Text.from_markup(str(prompt))
        return t_obj.plain
    except Exception:
        # Fallback to a basic string cleanup
        import re
        return re.sub(r"\[.*?\]", "", str(prompt))


def _active_palette_query(text: str) -> str:
    at_idx = _last_token_marker(text, "@")
    slash_idx = text.rfind("/", 0, at_idx if at_idx != -1 else len(text))
    idx = at_idx if at_idx > slash_idx else slash_idx
    return text[idx:] if idx != -1 else text


def ask_with_palette(
    prompt: str,
    context: str = "main",
    default: str = "",
    gate_pending: bool = False,
    header_ansi: str | None = None,
    compact: bool = False,
    force_down: bool = False,
) -> str:
    """
    A standalone TUI prompt using the workflow monitor's palette style.
    If header_ansi is provided, it runs in full-screen mode with that ANSI
    content displayed above the input field.
    """
    state = {
        "autocomplete_active": False,
        "autocomplete_items": [],
    }

    # Mutable scroll position for the header pane
    _scroll = {"offset": 0, "max": 0}

    def _on_text_changed(_buffer: Buffer):
        text = _buffer.text
        items, active = palette_autocomplete_snapshot(
            text, context=context, gate_pending=gate_pending, workspace_root=os.getcwd()
        )
        state["autocomplete_active"] = active
        state["autocomplete_items"] = items

    main_buffer = Buffer(
        document=Document("", cursor_position=0),
        on_text_changed=_on_text_changed,
    )

    kb = KeyBindings()

    @kb.add("c-c")
    @kb.add("escape")
    def _cancel(event) -> None:
        event.app.exit(result="")

    @kb.add("enter")
    def _submit(event) -> None:
        text = main_buffer.text.strip()
        event.app.exit(result=text or default)

    @kb.add("tab")
    def _tab(event) -> None:
        if state["autocomplete_active"] and state["autocomplete_items"]:
            # Find the first item that is not a section header
            real_items = [i for i in state["autocomplete_items"] if i[0] != "__sep__"]
            if real_items:
                first = real_items[0][0]
                text = main_buffer.text
                at_idx = _last_token_marker(text, "@")
                slash_idx = text.rfind("/", 0, at_idx if at_idx != -1 else len(text))
                replace_idx = at_idx if at_idx > slash_idx else slash_idx
                new_text = (text[:replace_idx] if replace_idx != -1 else "") + first
                main_buffer.set_document(
                    Document(new_text, cursor_position=len(new_text)),
                    bypass_readonly=True,
                )
                _on_text_changed(main_buffer)
                event.app.invalidate()

    @kb.add("pageup")
    def _page_up(event) -> None:
        _scroll["offset"] = max(0, _scroll["offset"] - 8)
        event.app.invalidate()

    @kb.add("pagedown")
    def _page_down(event) -> None:
        _scroll["offset"] = min(_scroll.get("max", 0), _scroll["offset"] + 8)
        event.app.invalidate()

    def _get_term_width() -> int:
        import shutil
        return shutil.get_terminal_size((120, 30)).columns

    def _sep_text():
        width = _get_term_width()
        right = "-" * max(0, width - 12)
        return to_formatted_text(
            ANSI(
                markup_to_ansi(
                    f"[#6495ED]---- [bold]aiteam[/bold] {right}[/#6495ED]",
                    width=width,
                )
            )
        )

    def _bottom_sep_text():
        width = _get_term_width()
        return to_formatted_text(
            ANSI(markup_to_ansi(f"[#6495ED]{'-' * width}[/#6495ED]", width=width))
        )

    sep_window = Window(
        content=FormattedTextControl(_sep_text, focusable=False),
        height=1,
        dont_extend_height=True,
    )
    bottom_sep_window = Window(
        content=FormattedTextControl(_bottom_sep_text, focusable=False),
        height=1,
        dont_extend_height=True,
    )

    def _get_valid_items():
        return [i[0] for i in state["autocomplete_items"] if i[0] != "__sep__"]

    before_input = _plain_prompt(prompt)
    input_row, attach_win = palette_gutter_input_row(
        buffer=main_buffer,
        before_input=before_input,
        get_valid_items=_get_valid_items,
    )

    show_popup = palette_popup_show_condition(lambda: bool(state["autocomplete_active"]))

    # Inline popup for compact mode
    inline_popup_body = make_command_palette_body(
        get_query=lambda: _active_palette_query(main_buffer.text),
        get_items=lambda: state["autocomplete_items"],  # type: ignore[return-value]
        width=POPUP_WIDTH,
    )
    inline_popup = ConditionalContainer(content=inline_popup_body, filter=show_popup)

    full_screen = False

    if header_ansi:
        clean_ansi = header_ansi.replace("\r\n", "\n")
        content = Window(
            content=_ScrollableAnsiControl(lambda: clean_ansi, _scroll),
            height=D(weight=1, min=1),
        )
        if force_down:
            spacer = Window(height=10, dont_extend_height=True)
            body = HSplit([content, sep_window, input_row, bottom_sep_window, spacer])
            is_down = True
        else:
            body = HSplit([content, sep_window, input_row, bottom_sep_window])
            is_down = False
        full_screen = True
    else:
        if compact:
            spacer = Window(height=10, dont_extend_height=True)
            body = HSplit([attach_win, spacer])
            is_down = True
        else:
            if force_down:
                spacer = Window(height=10, dont_extend_height=True)
                body = HSplit([sep_window, input_row, bottom_sep_window, spacer])
                is_down = True
            else:
                body = HSplit([sep_window, input_row, bottom_sep_window])
                is_down = False
        full_screen = False

    if is_down:
        if compact:
            float_top = 1
        else:
            # sep_window (1) + input_row (1) = 2.
            # So top=2 will draw the popup exactly covering the bottom_sep_window,
            # which looks seamless.
            float_top = 2
    else:
        float_top = None

    # Float popup
    popup_float = command_palette_float_attached(
        get_query=lambda: _active_palette_query(main_buffer.text),
        get_items=lambda: state["autocomplete_items"],  # type: ignore[return-value]
        show_filter=show_popup,
        width=POPUP_WIDTH,
        attach_to_window=attach_win,
        buffer=main_buffer,
        before_input=before_input,
        top=float_top,
        bottom=None if is_down else None, # Let command_palette_float_attached decide if not is_down
    )

    app = Application(
        layout=Layout(
            FloatContainer(content=body, floats=[popup_float]),
            focused_element=main_buffer,
        ),
        key_bindings=kb,
        style=palette_application_style(),
        full_screen=full_screen,
        color_depth=palette_application_color_depth(),
        mouse_support=False,
        erase_when_done=not full_screen,
    )

    try:
        result = app.run()
        return result or ""
    except Exception as e:
        # Re-raise to ensure prompt.py handles it correctly if it's a critical error
        # but for normal UI errors we might want to log it.
        # For now, let it fall back.
        raise e
