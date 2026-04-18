from __future__ import annotations

from typing import Any, Optional, Sequence, Union

from rich.console import Console

console = Console()
GLOBAL_BACK = "back"
GLOBAL_EXIT = "exit"


def normalize_global_command(raw: str) -> str:
    return (raw or "").strip().lower()


def ask_choice(
    prompt: Union[str, Any],
    choices: Sequence[str],
    *,
    default: Optional[str] = None,
    show_default: bool = True,
    allow_global: bool = True,
    **kwargs: Any,
) -> str:
    allowed = [str(c) for c in choices]
    if not allowed:
        raise ValueError("ask_choice requires at least one choice")
    d = str(default if default is not None else allowed[0])
    while True:
        suffix = f" [{d}]" if show_default and d else ""
        console.print(f"{prompt}{suffix}", end=" ")
        raw = normalize_global_command(input())
        if not raw:
            raw = d
        if allow_global and raw in (GLOBAL_BACK, GLOBAL_EXIT):
            return raw
        if raw in allowed:
            return str(raw)
        console.print("[yellow]Lựa chọn không hợp lệ, thử lại.[/yellow]")


__all__ = ["ask_choice", "normalize_global_command", "GLOBAL_BACK", "GLOBAL_EXIT"]
