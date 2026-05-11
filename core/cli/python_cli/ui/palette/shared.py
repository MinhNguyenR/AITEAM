"""Workflow monitor palette: autocomplete rules, chrome, Float, Application defaults."""
from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
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

from .items import POPUP_WIDTH, build_popup_items
from .lexer import CommandLexer
from .popup import make_command_palette_body, make_command_palette_float

COMMAND_PALETTE_CONTEXT_MONITOR = "monitor"
COMMAND_INPUT_MAX_HEIGHT = 4
_MENTION_EXTS = frozenset((".py", ".md", ".json", ".ts", ".js", ".html", ".css", ".tsx", ".jsx", ".txt"))
_MENTION_IGNORES = frozenset((".git", "__pycache__", "node_modules", ".venv", "venv", ".idea"))
_MENTION_CACHE_TTL_SEC = 8.0
_MENTION_MAX_FILES = 4000
_MENTION_CACHE: dict[str, tuple[float, list[str]]] = {}


def _get_commands_for_context(context: str) -> list[str]:
    """Return slash-command strings for *context* (used by tab completion)."""
    try:
        from core.cli.python_cli.ui.autocomplete import COMMAND_REGISTRY

        return [c for c, _ in COMMAND_REGISTRY.get(context, []) if c.startswith("/")]
    except Exception:
        return []


def palette_autocomplete_snapshot(
    text: str,
    *,
    context: str,
    gate_pending: bool,
    workspace_root: str | Path | None = None,
) -> tuple[list[tuple[str, str]], bool]:
    """Full palette list for slash input; visibility matches workflow monitor."""
    at_idx = _last_token_marker(text, "@")
    slash_idx = text.rfind("/", 0, at_idx if at_idx != -1 else len(text))

    if at_idx > slash_idx and context == "monitor":
        query = text[at_idx:]
        items = []
        q_lower = query.lower()
        q_body = q_lower[1:].replace("\\", "/")

        if "@codebase".startswith(q_lower):
            items.append(("@codebase", "workspace"))

        file_items = []
        for rel_path in _iter_workspace_mention_files(workspace_root):
            suggestion = f"@{rel_path}"
            rel_lower = rel_path.lower()
            base_lower = Path(rel_path).name.lower()
            if (
                suggestion.lower().startswith(q_lower)
                or (q_body and base_lower.startswith(q_body))
                or (q_body and q_body in rel_lower)
            ):
                parent = str(Path(rel_path).parent).replace("\\", "/")
                meta = "" if parent in ("", ".") else parent
                file_items.append((suggestion, meta))

        file_items.sort(key=lambda x: (Path(x[0][1:]).name.lower(), x[0].lower()))
        items.extend(file_items[:30])

        if not items:
            return [], False

        if len(items) == 1 and items[0][0].lower() == query.lower():
            return items, False

        final_items = [("__sep__", "Files & Workspace")] + items
        return final_items, True

    if slash_idx == -1:
        return [], False
    query = text[slash_idx:]
    items = build_popup_items(query=query, context=context, gate_pending=gate_pending)
    flat = [(c, d) for c, d in items if c != "__sep__"]
    if not flat:
        return items, False
    if len(flat) == 1 and flat[0][0].lower() == query.lower():
        return items, False
    return items, True


def _last_token_marker(text: str, marker: str) -> int:
    idx = text.rfind(marker)
    if idx == -1:
        return -1
    boundary = max(text.rfind(" "), text.rfind("\t"), text.rfind("\n"))
    return idx if idx > boundary else -1


def _iter_workspace_mention_files(workspace_root: str | Path | None) -> list[str]:
    """Return mentionable files under the caller's workspace root."""
    root = Path(workspace_root or ".").expanduser()
    try:
        root = root.resolve()
    except OSError:
        return []
    if not root.exists() or not root.is_dir():
        return []
    cache_key = str(root)
    now = time.monotonic()
    cached = _MENTION_CACHE.get(cache_key)
    if cached and now - cached[0] <= _MENTION_CACHE_TTL_SEC:
        return cached[1]

    out: list[str] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            continue
        for entry in entries:
            name = entry.name
            if name in _MENTION_IGNORES:
                continue
            try:
                is_dir = entry.is_dir()
                is_file = entry.is_file()
            except OSError:
                continue
            if is_dir:
                stack.append(entry)
            elif is_file and entry.suffix.lower() in _MENTION_EXTS:
                try:
                    rel = entry.resolve().relative_to(root)
                except (OSError, ValueError):
                    continue
                out.append(rel.as_posix())
                if len(out) >= _MENTION_MAX_FILES:
                    result = sorted(out, key=str.lower)
                    _MENTION_CACHE[cache_key] = (now, result)
                    return result
    result = sorted(out, key=str.lower)
    _MENTION_CACHE[cache_key] = (now, result)
    return result


def palette_command_input_height(
    *,
    buffer: Buffer,
    before_input: str,
    max_height: int = COMMAND_INPUT_MAX_HEIGHT,
) -> int:
    columns = max(20, shutil.get_terminal_size((120, 30)).columns - 2)
    prefix_len = len(before_input)
    line_count = 0
    for line in (buffer.text or "").splitlines() or [""]:
        visible_len = prefix_len + len(line)
        line_count += max(1, (visible_len + columns - 1) // columns)
    return max(1, min(max_height, line_count))


def palette_float_bottom(*, buffer: Buffer, before_input: str) -> int:
    return palette_command_input_height(buffer=buffer, before_input=before_input) + 2


def palette_buffer_input_center(*, buffer: Buffer, before_input: str, get_valid_items: Callable[[], list[str]] | None = None) -> Window:
    return Window(
        content=BufferControl(
            buffer=buffer,
            input_processors=[BeforeInput(before_input)],
            lexer=CommandLexer(get_valid_items),
            focusable=True,
        ),
        height=lambda: D.exact(
            palette_command_input_height(buffer=buffer, before_input=before_input)
        ),
        wrap_lines=True,
        dont_extend_height=True,
    )


def palette_gutter_input_row(*, buffer: Buffer, before_input: str, get_valid_items: Callable[[], list[str]] | None = None) -> tuple[VSplit, Window]:
    center = palette_buffer_input_center(buffer=buffer, before_input=before_input, get_valid_items=get_valid_items)

    def _gutter() -> Window:
        return Window(
            content=FormattedTextControl(
                lambda: [("fg:#6495ED", "|")],
                focusable=False,
            ),
            width=1,
            height=lambda: D.exact(
                palette_command_input_height(buffer=buffer, before_input=before_input)
            ),
            dont_extend_height=True,
        )

    row = VSplit(
        [_gutter(), center],
        height=lambda: D.exact(
            palette_command_input_height(buffer=buffer, before_input=before_input)
        ),
    )
    return row, center


def palette_popup_show_condition(
    autocomplete_active: Callable[[], bool],
    *,
    enabled_when: Callable[[], bool] | None = None,
) -> Condition:
    """Float filter: popup when active and optional extra gate."""

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


def palette_float_kwargs(
    attach_to_window: Window,
    *,
    buffer: Buffer | None = None,
    before_input: str = "",
    top: int | None = None,
    bottom: int | None = None,
) -> dict[str, Any]:
    b = bottom
    if b is None and top is None:
        b = (
            palette_float_bottom(buffer=buffer, before_input=before_input)
            if buffer is not None
            else 3
        )
    return {
        "left": 2,
        "bottom": b,
        "top": top,
        "attach_to_window": attach_to_window,
        "hide_when_covering_content": False,
    }


def command_palette_float_attached(
    *,
    get_query: Callable[[], str],
    get_items: Callable[[], List[Tuple[str, str]]],
    show_filter: Any,
    attach_to_window: Window,
    buffer: Buffer | None = None,
    before_input: str = "",
    width: int = POPUP_WIDTH,
    top: int | None = None,
    bottom: int | None = None,
) -> Any:
    return make_command_palette_float(
        get_query=get_query,
        get_items=get_items,
        show_filter=show_filter,
        width=width,
        frame_cls=CommandPaletteFrame,
        float_kwargs=palette_float_kwargs(
            attach_to_window,
            buffer=buffer,
            before_input=before_input,
            top=top,
            bottom=bottom,
        ),
    )
