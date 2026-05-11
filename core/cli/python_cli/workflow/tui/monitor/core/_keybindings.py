"""Key binding factory for the workflow monitor TUI."""
from __future__ import annotations

import re

from prompt_toolkit.document import Document as _Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.key_binding import KeyBindings

from ._constants import _CLEAR_TEXT_RE, _GATE_ACCEPTED
from ._utils import _r2a
from core.cli.python_cli.i18n import t
from core.cli.python_cli.ui.palette import _last_token_marker


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


def build_keybindings(app, *, _in_check: Condition) -> KeyBindings:
    """Build and return KeyBindings for the monitor app.

    *app* is the monitor application instance (has _write, _cmd_q, etc.).
    """
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
                app._write(f"[dim]X {t('cmd.clear_running')}[/dim]")
                buf.set_document(_Document(''), bypass_readonly=True)
                event.app.invalidate()
                return
            word = m.group(1)
            num_str = m.group(2)
            cmd_start = m.start()
            prefix = text[:cmd_start]
            if not word:
                buf.set_document(_Document(''), bypass_readonly=True)
                app._write(f"[dim]CLR {t('ui.cleared')}[/dim]")
                event.app.invalidate()
                return
            occurrence = int(num_str) if num_str else None
            if occurrence is None:
                _hits = [_m.start() for _m in re.finditer(re.escape(word), prefix, re.IGNORECASE)]
                if len(_hits) > 1:
                    n = len(_hits)
                    app._write(_r2a(
                        f"[yellow]{n} occurrences of [bold]\"{_esc(word)}\"[/bold] -- "
                        f"add number: /clear text {_esc(word)} 1"
                        f"  [dim](1=first  2=middle  3=last)[/dim][/yellow]"
                    ))
                    buf.set_document(_Document(''), bypass_readonly=True)
                    event.app.invalidate()
                    return
            pos = _find_cut_pos(prefix, word, occurrence)
            if pos is None:
                app._write(_r2a(f"[yellow]X {t('ui.not_found_in_input').format(word=_esc(word))}[/yellow]"))
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
            app._write(_r2a(preview))
            buf.set_document(_Document(new_text, cursor_position=len(new_text)), bypass_readonly=True)
            event.app.invalidate()
            return
        buf.validate_and_handle()

    @kb.add("c-c", eager=True)
    def _ctrl_c(event):
        if app._log_mode:
            app._close_log(); return
        if app._check_mode:
            app._close_check(); return
        from ....runtime import session as ws
        snap = ws.get_pipeline_snapshot()
        if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", ""):
            import time as _time
            now = _time.time()
            if now - getattr(app, "_last_ctrl_c_ts", 0.0) <= 3.0:
                ws.request_pipeline_stop()
                app._write("[bold yellow]Stopping pipeline...[/bold yellow]")
                event.app.exit()
                return
            app._last_ctrl_c_ts = now
            app._write("[bold yellow]Pipeline đang chạy. Bấm Ctrl+C lần nữa trong 3 giây để dừng toàn bộ pipeline.[/bold yellow]")
            app._scroll_offset = 0
        else:
            event.app.exit()

    @kb.add("tab", eager=True, filter=~_in_check)
    def _tab_complete(event):
        items = app._autocomplete_items
        first = next((c for c, _ in items if c != "__sep__"), None)
        if first and app._main_buffer:
            text = app._main_buffer.text
            at_idx = _last_token_marker(text, "@")
            slash_idx = text.rfind("/", 0, at_idx if at_idx != -1 else len(text))
            replace_idx = at_idx if at_idx > slash_idx else slash_idx
            new_text = (text[:replace_idx] if replace_idx != -1 else "") + first
            app._main_buffer.set_document(
                _Document(new_text, cursor_position=len(new_text)),
                bypass_readonly=True,
            )
            event.app.invalidate()

    @kb.add("escape", eager=True)
    def _escape(event):
        if app._autocomplete_active:
            app._autocomplete_active = False
            app._autocomplete_items = []
            event.app.invalidate()
        elif app._log_mode:
            app._close_log()

    @kb.add("c-up", eager=True)
    @kb.add("up", eager=True)
    def _scroll_up(event):
        if app._log_mode:
            n = len(app._log_lines)
            app._log_scroll = min(app._log_scroll + 3, max(0, n - 1))
        else:
            n = app._cached_display_count or 1
            app._scroll_offset = min(app._scroll_offset + 3, max(0, n - 1))
        event.app.invalidate()

    @kb.add("c-down", eager=True)
    @kb.add("down", eager=True)
    def _scroll_down(event):
        if app._log_mode:
            app._log_scroll = max(0, app._log_scroll - 3)
        else:
            app._scroll_offset = max(0, app._scroll_offset - 3)
        event.app.invalidate()

    @kb.add("c-end", eager=True)
    def _snap_bottom(event):
        if app._log_mode:
            app._log_scroll = 0
        else:
            app._scroll_offset = 0
        event.app.invalidate()

    @kb.add("pageup", eager=True)
    def _page_up(event):
        if not app._log_mode:
            n = app._cached_display_count or 1
            app._scroll_offset = min(app._scroll_offset + 10, max(0, n - 1))
            event.app.invalidate()

    @kb.add("pagedown", eager=True)
    def _page_down(event):
        if not app._log_mode:
            app._scroll_offset = max(0, app._scroll_offset - 10)
            event.app.invalidate()

    @kb.add("c-up", eager=True, filter=_in_check)
    @kb.add("up", eager=True, filter=_in_check)
    def _check_up(event):
        n = len(app._check_lines)
        app._check_scroll = min(app._check_scroll + 3, max(0, n - 1))
        event.app.invalidate()

    @kb.add("c-down", eager=True, filter=_in_check)
    @kb.add("down", eager=True, filter=_in_check)
    def _check_down(event):
        app._check_scroll = max(0, app._check_scroll - 3)
        event.app.invalidate()

    @kb.add("pageup", eager=True, filter=_in_check)
    def _check_page_up(event):
        n = len(app._check_lines)
        app._check_scroll = min(app._check_scroll + 12, max(0, n - 1))
        event.app.invalidate()

    @kb.add("pagedown", eager=True, filter=_in_check)
    def _check_page_down(event):
        app._check_scroll = max(0, app._check_scroll - 12)
        event.app.invalidate()

    @kb.add("escape", filter=_in_check)
    @kb.add("c-c", filter=_in_check, eager=True)
    def _check_close(event):
        app._close_check()

    return kb
