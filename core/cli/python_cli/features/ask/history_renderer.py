from __future__ import annotations

from typing import Dict, List

from rich.box import ROUNDED
from rich.panel import Panel
from rich.rule import Rule
from rich.style import Style
from rich.text import Text

from core.cli.python_cli.ui.palette import ask_with_palette
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, console
from core.cli.python_cli.i18n import t

_HISTORY_PREVIEW_MAX_CHARS = 180


def ask_command_hints(mode: str) -> str:
    switch = "ask thinking" if mode == "standard" else "ask standard"
    return f"[dim]{switch}  ·  back  ·  exit[/dim]"


def render_history_lines(chat: Dict, limit: int = 12) -> List[str]:
    lines: List[str] = []
    for m in chat.get("messages", [])[-limit:]:
        role  = m.get("role", "user")
        label = t("ask.label_you") if role == "user" else t("ask.label_ai")
        body  = (m.get("content", "") or "").strip()
        if len(body) > _HISTORY_PREVIEW_MAX_CHARS:
            body = body[: _HISTORY_PREVIEW_MAX_CHARS - 3] + "..."
        lines.append(f"{label}: {body}")
    return lines


def _print_message_panel(index: int, role: str, content: str, *, max_chars: int = 0) -> None:
    is_user  = role == "user"
    label    = t("ask.label_you") if is_user else t("ask.label_ai")
    border   = PASTEL_CYAN if is_user else PASTEL_BLUE
    label_s  = Style(color=PASTEL_CYAN, bold=True) if is_user else Style(color=SOFT_WHITE, bold=True)
    body     = (content or "").strip()
    if max_chars > 0 and len(body) > max_chars:
        body = body[: max_chars - 3] + "..."
    if not body:
        body = t("ui.empty")
    inner = Text.assemble((f"{label}\n", label_s), (body, Style(color=SOFT_WHITE)))
    console.print(
        Panel(
            inner,
            title=f"[dim]#{index}[/dim]",
            title_align="right",
            border_style=border,
            box=ROUNDED,
            padding=(0, 1),
        )
    )


def _render_loaded_history(chat: dict, limit: int = 12) -> None:
    messages = list(chat.get("messages") or [])
    if not messages:
        return
    console.print(Rule(f"[dim]{t('ask.history_rule')}[/dim]", style=PASTEL_BLUE))
    tail = messages[-limit:]
    base = len(messages) - len(tail) + 1
    for j, m in enumerate(tail):
        idx  = base + j
        role = m.get("role", "user")
        if role not in ("user", "assistant"):
            continue
        _print_message_panel(idx, role, m.get("content", ""), max_chars=_HISTORY_PREVIEW_MAX_CHARS)
    console.print()


def _ask_input_with_header(header_text: str, mode: str, *, compact: bool = False) -> str:
    hints = ask_command_hints(mode)
    label_you = t("ask.label_you")

    if compact:
        console.print(hints)
        return ask_with_palette(f"{label_you}  >  ", context="ask_chat")

    console.print(Rule(f"[{PASTEL_CYAN}]{header_text}[/{PASTEL_CYAN}]", style=PASTEL_BLUE))
    console.print(hints)
    console.print()
    return ask_with_palette(f"{label_you}  >  ", context="ask_chat")
