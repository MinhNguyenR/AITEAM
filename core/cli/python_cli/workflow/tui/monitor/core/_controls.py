"""prompt_toolkit UIControl subclasses for scrollable history and check view."""
from __future__ import annotations

from prompt_toolkit.data_structures import Point
from prompt_toolkit.layout.controls import UIContent, UIControl
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType


class _HistoryControl(UIControl):
    """Colored, scrollable content area.

    scroll_offset=0  -> cursor at last line (auto-follow)
    scroll_offset>0  -> user scrolled up (cursor above last line)
    """

    def __init__(self, app: "WorkflowListApp") -> None:  # type: ignore[name-defined]
        self._app = app
        self._hist_cache: list = []
        self._hist_cache_len: int = -1
        self._log_cache: list = []
        self._log_cache_len: int = -1
        self._live_cache: list = []
        self._live_cache_raw: str = ""

    def create_content(self, width: int, height: int) -> UIContent:
        if self._app._log_mode:
            raw_lines = self._app._log_lines
            offset = self._app._log_scroll
            if len(raw_lines) != self._log_cache_len:
                cache: list = []
                for ansi_str in raw_lines:
                    for part in ansi_str.rstrip("\n").split("\n"):
                        cache.append(to_formatted_text(ANSI(part)))
                self._log_cache = cache
                self._log_cache_len = len(raw_lines)
            display = self._log_cache
        else:
            hist = self._app._history_raw
            live = self._app._live_raw
            if len(hist) != self._hist_cache_len:
                cache = []
                for ansi_str in hist:
                    for part in ansi_str.rstrip("\n").split("\n"):
                        cache.append(to_formatted_text(ANSI(part)))
                self._hist_cache = cache
                self._hist_cache_len = len(hist)
            if live:
                if live != self._live_cache_raw:
                    self._live_cache = [
                        to_formatted_text(ANSI(p))
                        for p in live.rstrip("\n").split("\n")
                    ]
                    self._live_cache_raw = live
                display = self._hist_cache + self._live_cache
            else:
                if self._live_cache_raw:
                    self._live_cache = []
                    self._live_cache_raw = ""
                display = self._hist_cache
            offset = self._app._scroll_offset
        n = len(display)
        self._app._cached_display_count = n
        _d = display

        def get_line(i: int) -> list:
            return _d[i] if 0 <= i < len(_d) else []

        cursor_y = max(0, n - 1 - offset)
        return UIContent(
            get_line=get_line,
            line_count=max(1, n),
            cursor_position=Point(x=0, y=cursor_y),
            show_cursor=False,
        )

    def is_focusable(self) -> bool:
        return False

    def mouse_handler(self, mouse_event: MouseEvent):
        if self._app._log_mode:
            n = len(self._app._log_lines)
            if mouse_event.event_type == MouseEventType.SCROLL_UP:
                self._app._log_scroll = min(self._app._log_scroll + 3, max(0, n - 1))
                if self._app._app: self._app._app.invalidate()
                return None
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self._app._log_scroll = max(0, self._app._log_scroll - 3)
                if self._app._app: self._app._app.invalidate()
                return None
        else:
            n = self._app._cached_display_count or 1
            if mouse_event.event_type == MouseEventType.SCROLL_UP:
                self._app._scroll_offset = min(self._app._scroll_offset + 3, max(0, n - 1))
                if self._app._app: self._app._app.invalidate()
                return None
            elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
                self._app._scroll_offset = max(0, self._app._scroll_offset - 3)
                if self._app._app: self._app._app.invalidate()
                return None
        return NotImplemented


class _CheckControl(UIControl):
    """Full-screen context.md viewer content."""

    def __init__(self, app: "WorkflowListApp") -> None:  # type: ignore[name-defined]
        self._app = app

    def create_content(self, width: int, height: int) -> UIContent:
        lines_raw = self._app._check_lines
        display: list[list] = []
        for raw in lines_raw:
            for part in raw.rstrip("\n").split("\n"):
                display.append(to_formatted_text(ANSI(part)))
        n = len(display)
        _d = display

        def get_line(i: int) -> list:
            return _d[i] if 0 <= i < len(_d) else []

        offset = self._app._check_scroll
        cursor_y = max(0, n - 1 - offset)
        return UIContent(
            get_line=get_line,
            line_count=max(1, n),
            cursor_position=Point(x=0, y=cursor_y),
            show_cursor=False,
        )

    def is_focusable(self) -> bool:
        return False

    def mouse_handler(self, mouse_event: MouseEvent):
        n = len(self._app._check_lines)
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self._app._check_scroll = min(self._app._check_scroll + 3, max(0, n - 1))
            if self._app._app:
                self._app._app.invalidate()
            return None
        if mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self._app._check_scroll = max(0, self._app._check_scroll - 3)
            if self._app._app:
                self._app._app.invalidate()
            return None
        return NotImplemented
