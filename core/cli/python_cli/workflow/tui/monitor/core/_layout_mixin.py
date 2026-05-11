"""Mixin: _build_app -- constructs the prompt_toolkit Application."""
from __future__ import annotations


from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document as _Document
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer, FloatContainer, HSplit, Window,
)
from prompt_toolkit.layout.controls import (
    BufferControl, FormattedTextControl,
)
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from ._constants import _GATE_WAITING
from core.cli.python_cli.i18n import t
from ._controls import _CheckControl, _HistoryControl
from ._utils import _r2a
from ._keybindings import build_keybindings
from ..helpers import _project_root_default
from core.cli.python_cli.ui.palette import (
    COMMAND_PALETTE_CONTEXT_MONITOR,
    POPUP_WIDTH,
    command_palette_float_attached,
    palette_application_color_depth,
    palette_application_style,
    palette_autocomplete_snapshot,
    palette_float_bottom,
    palette_gutter_input_row,
    palette_popup_show_condition,
    _last_token_marker,
)
class _LayoutMixin:


    def _build_app(self) -> Application:
        _prompt_prefix = "> "
        _log_hint_ansi = _r2a(
            f"[bold]{t('cmd.log_header')}[/bold]  [dim]{t('cmd.log_hint')}[/dim]"
        )


        def _hint_text():
            if self._log_mode:
                return to_formatted_text(ANSI(_log_hint_ansi))
            return to_formatted_text(ANSI(self._hint_raw or ""))


        hint_win = Window(content=FormattedTextControl(_hint_text, focusable=False), height=1)
        content_win = Window(content=_HistoryControl(self), dont_extend_height=False)


        def _accept_main(buff):
            text = buff.text
            if text == getattr(self, "_pasted_placeholder", "") and getattr(self, "_pasted_payload", ""):
                text = self._pasted_payload
            self._pasted_payload = ""
            self._pasted_placeholder = ""
            self._autocomplete_active = False
            self._autocomplete_items = []
            if text:
                self._cmd_q.put(text)


        autocomplete_float = None
        self._main_buffer = Buffer(
            multiline=False,
            accept_handler=_accept_main,
        )


        def _on_text_changed(_buff):
            current_text = self._main_buffer.text
            if "\n" in current_text:
                line_count = len(current_text.splitlines())
                if line_count > 6 and not getattr(self, "_paste_collapse_used", False):
                    extra = line_count - 6
                    placeholder = "[Pasted text]" if extra <= 0 else f"[Pasted text + {extra} lines]"
                    self._paste_collapse_used = True
                    self._pasted_payload = current_text
                    self._pasted_placeholder = placeholder
                    self._main_buffer.set_document(
                        _Document(placeholder, cursor_position=len(placeholder)),
                        bypass_readonly=True,
                    )
                    if self._app:
                        self._app.invalidate()
                    return
            items, active = palette_autocomplete_snapshot(
                self._main_buffer.text,
                context=COMMAND_PALETTE_CONTEXT_MONITOR,
                gate_pending=getattr(self, "_gate_pending", False),
                workspace_root=_project_root_default(),
            )
            self._autocomplete_items = items
            self._autocomplete_active = active
            if autocomplete_float is not None:
                autocomplete_float.bottom = palette_float_bottom(
                    buffer=self._main_buffer,
                    before_input=_prompt_prefix,
                )
            if self._app:
                self._app.invalidate()


        self._main_buffer.on_text_changed += _on_text_changed
        input_win, _input_ctrl_win = palette_gutter_input_row(
            buffer=self._main_buffer,
            before_input=_prompt_prefix,
        )


        def _sep_text():
            try:
                w = self._app.output.get_size().columns if self._app else 120
            except Exception:
                w = 120
            base = "[#6495ED]---- [bold]aiteam[/bold][/#6495ED]"
            base_plain_len = 12
            right = "-" * max(0, w - base_plain_len)
            return to_formatted_text(ANSI(_r2a(f"{base} [#6495ED]{right}[/#6495ED]")))


        sep_win = Window(content=FormattedTextControl(_sep_text, focusable=False), height=1)


        def _bottom_sep_text():
            try:
                w = self._app.output.get_size().columns if self._app else 120
            except Exception:
                w = 120
            return to_formatted_text(ANSI(_r2a(f"[#6495ED]{'-' * w}[/#6495ED]")))


        bottom_sep_win = Window(
            content=FormattedTextControl(_bottom_sep_text, focusable=False),
            height=1,
        )


        def _check_hint_text():
            status = t('cmd.check_status_editing') if self._check_auto_refresh else t('cmd.check_status_viewing')
            return to_formatted_text(ANSI(
                _r2a(f"[bold]context.md[/bold]  {status}  [bold yellow]-- {t('cmd.check_hint_labels')}[/bold yellow]")
            ))


        check_hint_win    = Window(content=FormattedTextControl(_check_hint_text, focusable=False), height=1)
        check_content_win = Window(content=_CheckControl(self))


        _check_hints_ansi = _r2a(f"[dim]{t('cmd.check_hint_full')}[/dim]")
        check_hints_win = Window(
            content=FormattedTextControl(lambda: to_formatted_text(ANSI(_check_hints_ansi)), focusable=False),
            height=1,
        )
        self._check_buffer = Buffer(
            multiline=False,
            accept_handler=lambda buff: self._cmd_q.put("__check__:" + buff.text),
        )
        check_input_win = Window(
            content=BufferControl(
                buffer=self._check_buffer,
                input_processors=[BeforeInput(_prompt_prefix)],
                focusable=True,
            ),
            height=1,
        )


        @Condition
        def _in_check():
            return self._check_mode


        @Condition
        def _in_workflow():
            return not self._check_mode


        _show_popup = palette_popup_show_condition(
            lambda: self._autocomplete_active,
            enabled_when=lambda: not self._check_mode,
        )


        # -- command palette (implementation in ui.palette.shared) -------------


        def _palette_query() -> str:
            text = self._main_buffer.text if self._main_buffer else ""
            at_idx = _last_token_marker(text, "@")
            slash_idx = text.rfind("/", 0, at_idx if at_idx != -1 else len(text))
            idx = at_idx if at_idx > slash_idx else slash_idx
            return text[idx:] if idx != -1 else ""


        autocomplete_float = command_palette_float_attached(
            get_query=_palette_query,
            get_items=lambda: self._autocomplete_items,
            show_filter=_show_popup,
            width=POPUP_WIDTH,
            attach_to_window=_input_ctrl_win,
            buffer=self._main_buffer,
            before_input=_prompt_prefix,
        )


        _spacer_win = Window(height=1)
        main_layout = ConditionalContainer(
            content=HSplit([content_win, _spacer_win, sep_win, input_win, bottom_sep_win]),
            filter=_in_workflow,
        )
        check_layout = ConditionalContainer(
            content=HSplit([check_hint_win, check_content_win, check_hints_win, check_input_win]),
            filter=_in_check,
        )


        layout = Layout(
            FloatContainer(
                content=HSplit([main_layout, check_layout]),
                floats=[autocomplete_float],
            ),
            focused_element=self._main_buffer,
        )


        kb = build_keybindings(self, _in_check=_in_check)

        return Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            color_depth=palette_application_color_depth(),
            style=palette_application_style(),
            mouse_support=False,
            enable_page_navigation_bindings=False,
        )
