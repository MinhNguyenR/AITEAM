"""Mixin: _build_app — constructs the prompt_toolkit Application."""
from __future__ import annotations

import re

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
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.lexers import Lexer as _Lexer
from ._constants import _CLEAR_TEXT_RE, _GATE_WAITING
from core.cli.python_cli.i18n import t
from ._controls import _CheckControl, _HistoryControl
from ._utils import _r2a
from core.cli.python_cli.ui.palette import (
    COMMAND_PALETTE_CONTEXT_MONITOR,
    POPUP_WIDTH,
    command_palette_float_attached,
    palette_application_color_depth,
    palette_application_style,
    palette_autocomplete_snapshot,
    palette_gutter_input_row,
    palette_popup_show_condition,
)


# ── /clear text helper ────────────────────────────────────────────────────────
def _find_cut_pos(text: str, word: str, occurrence: int | None) -> int | None:
    """Return the start position in *text* where the cut should happen."""
    positions = [m.start() for m in re.finditer(re.escape(word), text, re.IGNORECASE)]
    if not positions:
        return None
    if len(positions) == 1:
        return positions[0]
    if occurrence is not None:
        if occurrence <= 1:
            return positions[0]
        if occurrence >= 3:
            return positions[-1]
        return positions[len(positions) // 2]
    prev_end, best_len, best_pos = 0, -1, positions[0]
    for p in positions:
        if p - prev_end > best_len:
            best_len = p - prev_end
            best_pos = p
        prev_end = p + len(word)
    return best_pos
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
            self._autocomplete_active = False
            self._autocomplete_items = []
            if text:
                self._cmd_q.put(text)

        self._main_buffer = Buffer(
            multiline=False,
            accept_handler=_accept_main,
        )

        def _on_text_changed(_buff):
            items, active = palette_autocomplete_snapshot(
                self._main_buffer.text,
                context=COMMAND_PALETTE_CONTEXT_MONITOR,
                gate_pending=getattr(self, "_gate_pending", False),
            )
            self._autocomplete_items = items
            self._autocomplete_active = active
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
            right = "─" * max(0, w - 12)
            return to_formatted_text(ANSI(_r2a(f"[dim]──── [bold]aiteam[/bold] {right}[/dim]")))

        sep_win = Window(content=FormattedTextControl(_sep_text, focusable=False), height=1)

        def _bottom_sep_text():
            try:
                w = self._app.output.get_size().columns if self._app else 120
            except Exception:
                w = 120
            return to_formatted_text(ANSI(_r2a(f"[dim]{'─' * w}[/dim]")))

        _bottom_sep_win = Window(content=FormattedTextControl(_bottom_sep_text, focusable=False), height=1)

        def _check_hint_text():
            status = t('cmd.check_status_editing') if self._check_auto_refresh else t('cmd.check_status_viewing')
            return to_formatted_text(ANSI(
                _r2a(f"[bold]context.md[/bold]  {status}  [bold yellow]— {t('cmd.check_hint_labels')}[/bold yellow]")
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

        # ── command palette (implementation in ui.palette.shared) ─────────────

        autocomplete_float = command_palette_float_attached(
            get_query=lambda: self._main_buffer.text if self._main_buffer else "",
            get_items=lambda: self._autocomplete_items,
            show_filter=_show_popup,
            width=POPUP_WIDTH,
            attach_to_window=_input_ctrl_win,
        )

        _spacer_win = Window(height=1)
        main_layout = ConditionalContainer(
            content=HSplit([content_win, _spacer_win, sep_win, input_win, _bottom_sep_win]),
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

        kb = KeyBindings()

        @kb.add("enter", eager=True, filter=~_in_check)
        def _enter(event):
            from rich.markup import escape as _esc
            buf = event.app.current_buffer
            text = buf.text
            m = _CLEAR_TEXT_RE.search(text)
            if m:
                from ....runtime import session as ws
                _snap_ct = ws.get_pipeline_snapshot()
                if str(_snap_ct.get("active_step") or "idle") not in ("idle", "end_failed", ""):
                    self._write(f"[dim]✗ {t('cmd.clear_running')}[/dim]")
                    buf.set_document(_Document(''), bypass_readonly=True)
                    event.app.invalidate()
                    return
                word = m.group(1)
                num_str = m.group(2)
                cmd_start = m.start()
                prefix = text[:cmd_start]
                if not word:
                    buf.set_document(_Document(''), bypass_readonly=True)
                    self._write(f"[dim]CLR {t('ui.cleared')}[/dim]")
                    event.app.invalidate()
                    return
                occurrence = int(num_str) if num_str else None
                pos = _find_cut_pos(prefix, word, occurrence)
                if pos is None:
                    self._write(_r2a(f"[yellow]✗ {t('ui.not_found_in_input').format(word=_esc(word))}[/yellow]"))
                    event.app.invalidate()
                    return
                new_text = prefix[:pos]
                word_actual = prefix[pos:pos + len(word)]
                rest = prefix[pos + len(word):] + text[cmd_start:]
                preview = (
                    f"[dim]CUT: [/dim] {_esc(new_text)}"
                    f"[bold yellow]{_esc(word_actual)}[/bold yellow]"
                    f"[dim]{_esc(rest)}[/dim]"
                )
                self._write(_r2a(preview))
                buf.set_document(_Document(new_text, cursor_position=len(new_text)), bypass_readonly=True)
                event.app.invalidate()
                return
            buf.validate_and_handle()

        @kb.add("c-c", eager=True)
        def _ctrl_c(event):
            if self._log_mode:
                self._close_log(); return
            if self._check_mode:
                self._close_check(); return
            from ....runtime import session as ws
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", ""):
                self._ask_exit_inline()
            else:
                event.app.exit()

        @kb.add("tab", eager=True, filter=~_in_check)
        def _tab_complete(event):
            """Complete input with the first suggested command."""
            items = self._autocomplete_items
            first = next((c for c, _ in items if c != "__sep__"), None)
            if first and self._main_buffer:
                self._main_buffer.set_document(
                    _Document(first, cursor_position=len(first)),
                    bypass_readonly=True,
                )
                event.app.invalidate()

        @kb.add("escape", eager=True)
        def _escape(event):
            if self._autocomplete_active:
                self._autocomplete_active = False
                self._autocomplete_items = []
                event.app.invalidate()
            elif self._log_mode:
                self._close_log()

        @kb.add("c-up", eager=True)
        @kb.add("up", eager=True)
        def _scroll_up(event):
            if self._log_mode:
                n = len(self._log_lines)
                self._log_scroll = min(self._log_scroll + 3, max(0, n - 1))
            else:
                n = self._cached_display_count or 1
                self._scroll_offset = min(self._scroll_offset + 3, max(0, n - 1))
            event.app.invalidate()

        @kb.add("c-down", eager=True)
        @kb.add("down", eager=True)
        def _scroll_down(event):
            if self._log_mode:
                self._log_scroll = max(0, self._log_scroll - 3)
            else:
                self._scroll_offset = max(0, self._scroll_offset - 3)
            event.app.invalidate()

        @kb.add("c-end", eager=True)
        def _snap_bottom(event):
            if self._log_mode:
                self._log_scroll = 0
            else:
                self._scroll_offset = 0
            event.app.invalidate()

        @kb.add("pageup", eager=True)
        def _page_up(event):
            if not self._log_mode:
                n = self._cached_display_count or 1
                self._scroll_offset = min(self._scroll_offset + 10, max(0, n - 1))
                event.app.invalidate()

        @kb.add("pagedown", eager=True)
        def _page_down(event):
            if not self._log_mode:
                self._scroll_offset = max(0, self._scroll_offset - 10)
                event.app.invalidate()

        @kb.add("c-up", eager=True, filter=_in_check)
        def _check_up(event):
            n = len(self._check_lines)
            self._check_scroll = min(self._check_scroll + 1, max(0, n - 1))
            event.app.invalidate()

        @kb.add("c-down", eager=True, filter=_in_check)
        def _check_down(event):
            self._check_scroll = max(0, self._check_scroll - 1)
            event.app.invalidate()

        @kb.add("escape", filter=_in_check)
        @kb.add("c-c", filter=_in_check, eager=True)
        def _check_close(event):
            self._close_check()

        return Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            color_depth=palette_application_color_depth(),
            style=palette_application_style(),
            mouse_support=False,
            enable_page_navigation_bindings=False,
        )
