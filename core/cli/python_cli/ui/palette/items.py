from __future__ import annotations

from typing import List, Tuple

from core.cli.python_cli.i18n import t
from core.cli.python_cli.ui.autocomplete import COMMAND_REGISTRY, get_popup_sections

from .styles import (
    PALETTE_BG,
    PALETTE_CMD_BOLD,
    PALETTE_CMD_TAIL,
    PALETTE_DESC,
    PALETTE_FRAME_FG,
)

POPUP_WIDTH = 64

_GLOBAL_SLASH = frozenset({"/back", "/exit"})
_SHUTDOWN = "/shutdown"

# Commands that go in the "Tasks" group for the main menu
_MAIN_TASKS = frozenset({"/start", "/check", "/workflow"})
# Commands that go in the "Info & utilities" group for the main menu
_MAIN_INFO = frozenset({"/status", "/info", "/dashboard", "/settings", "/help"})

_SECTION_HEADER_KEYS = frozenset({
    "mode",
    "check",
    "support",
    "global",
    "palette_main",
    "palette_cmds",
    "palette_main_tasks",
    "palette_main_info",
})


def _split_registry_into_sections(
    context: str,
) -> list[tuple[str, list[tuple[str, str]]]]:
    if context == "monitor":
        return get_popup_sections()
    raw = COMMAND_REGISTRY.get(context, [])
    rows = [(c, t(dk)) for c, dk in raw]

    if context == "main":
        tasks = [(c, d) for c, d in rows if c in _MAIN_TASKS]
        info  = [(c, d) for c, d in rows if c in _MAIN_INFO]
        glo   = [(c, d) for c, d in rows if c in _GLOBAL_SLASH or c == _SHUTDOWN]
        out: list[tuple[str, list[tuple[str, str]]]] = []
        if tasks:
            out.append(("palette_main_tasks", tasks))
        if info:
            out.append(("palette_main_info", info))
        if glo:
            out.append(("global", glo))
        return out

    nav = [(c, d) for c, d in rows if c not in _GLOBAL_SLASH and c != _SHUTDOWN]
    glo = [(c, d) for c, d in rows if c in _GLOBAL_SLASH or c == _SHUTDOWN]
    out = []
    if nav:
        out.append(("palette_cmds", nav))
    if glo:
        out.append(("global", glo))
    return out


def build_popup_items_all(
    context: str = "main",
    gate_pending: bool = False,
) -> List[Tuple[str, str]]:
    """Full slash-command list for *context* (same as query ``\"/\"``)."""
    return build_popup_items("/", context=context, gate_pending=gate_pending)


def build_popup_items(
    query: str,
    context: str = "main",
    gate_pending: bool = False,
) -> List[Tuple[str, str]]:
    sections = _split_registry_into_sections(context)

    if context == "monitor" and gate_pending:
        for name, cmds in sections:
            if name == "check":
                cmds.extend(
                    [
                        ("/accept", t("context.accept_desc").split(" — ")[0]),
                        ("/delete", t("context.delete_desc").split(" — ")[0]),
                    ]
                )

    q = query.lower()
    showing_all = q == "/"

    result: List[Tuple[str, str]] = []
    for name, items in sections:
        if showing_all:
            matched = items
        else:
            matched = [(c, d) for c, d in items if c.lower().startswith(q)]

        if matched:
            if showing_all:
                if name in _SECTION_HEADER_KEYS:
                    header = t(f"menu.{name}.desc").split(" — ")[0].split(" | ")[0]
                else:
                    header = str(name)
                result.append(("__sep__", header))
            result.extend(matched)
    return result


def render_popup_text(
    query: str,
    items: List[Tuple[str, str]],
    pad_min: int = 12,
) -> List[Tuple[str, str]]:
    if not items:
        return [("", " ")]

    flat = [(c, d) for c, d in items if c != "__sep__"]
    if not flat:
        return [("", " ")]

    q_len = len(query)
    pad = max(max(len(c) for c, _ in flat) + 2, pad_min)

    result: List[Tuple[str, str]] = []
    first = True
    first_section = True
    for cmd, desc in items:
        if cmd == "__sep__":
            if not first:
                result.append(("", "\n"))
            if not first_section:
                result.append(("", "\n"))
            first_section = False
            result.append((f"fg:{PALETTE_DESC} underline", f" {desc}"))
        else:
            if not first:
                result.append(("", "\n"))
            padded = cmd.ljust(pad)
            if q_len <= len(cmd):
                result.append((PALETTE_CMD_BOLD, padded[:q_len]))
                result.append((PALETTE_CMD_TAIL, padded[q_len:]))
            else:
                result.append((PALETTE_CMD_BOLD, cmd))
                result.append((PALETTE_CMD_TAIL, " " * (pad - len(cmd))))
            if desc:
                cap = max(8, POPUP_WIDTH - pad - 2)
                raw = desc.split(" | ")[0].split(" — ")[0].strip()
                short_desc = raw if len(raw) <= cap else raw[: cap - 1] + "…"
                result.append((f"fg:{PALETTE_DESC}", short_desc))
        first = False
    return result


def ptk_popup_window_style() -> str:
    return f"bg:{PALETTE_BG}"


def ptk_frame_style() -> str:
    return f"bg:{PALETTE_BG} fg:{PALETTE_FRAME_FG}"


def ptk_frame_border_style_key() -> str:
    return PALETTE_FRAME_FG
