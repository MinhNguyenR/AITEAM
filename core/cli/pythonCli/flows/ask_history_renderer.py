from __future__ import annotations

import importlib
from typing import Dict, List

from rich.box import ROUNDED, SIMPLE
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.style import Style
from rich.text import Text

from core.cli.pythonCli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, BRIGHT_BLUE, console

try:
    _pt_module = importlib.import_module("prompt_toolkit")
    pt_prompt = getattr(_pt_module, "prompt", None)
except (ImportError, AttributeError):
    pt_prompt = None

_HISTORY_PREVIEW_MAX_CHARS = 180


def ask_command_hints(mode: str) -> str:
    switch = "ask thinking" if mode == "standard" else "ask standard"
    return f"[dim]{switch}  ·  back  ·  exit[/dim]"


def render_history_lines(chat: Dict, limit: int = 12) -> List[str]:
    lines: List[str] = []
    for m in chat.get("messages", [])[-limit:]:
        role  = m.get("role", "user")
        label = "You" if role == "user" else "AI-team"
        body  = (m.get("content", "") or "").strip()
        if len(body) > _HISTORY_PREVIEW_MAX_CHARS:
            body = body[: _HISTORY_PREVIEW_MAX_CHARS - 3] + "..."
        lines.append(f"{label}: {body}")
    return lines


def _print_message_panel(index: int, role: str, content: str, *, max_chars: int = 0) -> None:
    is_user  = role == "user"
    label    = "You" if is_user else "AI-team"
    border   = PASTEL_CYAN if is_user else PASTEL_BLUE
    label_s  = Style(color=PASTEL_CYAN, bold=True) if is_user else Style(color=SOFT_WHITE, bold=True)
    body     = (content or "").strip()
    if max_chars > 0 and len(body) > max_chars:
        body = body[: max_chars - 3] + "..."
    if not body:
        body = "(empty)"
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
    console.print(Rule("[dim]conversation history[/dim]", style=PASTEL_BLUE))
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
    if compact:
        console.print(hints)
        if pt_prompt:
            return pt_prompt("You  >  ")
        return Prompt.ask(f"[{PASTEL_CYAN}]You[/{PASTEL_CYAN}]")
    console.print(Rule(f"[{PASTEL_CYAN}]{header_text}[/{PASTEL_CYAN}]", style=PASTEL_BLUE))
    console.print(hints)
    console.print()
    if pt_prompt:
        return pt_prompt("You  >  ")
    return Prompt.ask(f"[{PASTEL_CYAN}]You[/{PASTEL_CYAN}]")
