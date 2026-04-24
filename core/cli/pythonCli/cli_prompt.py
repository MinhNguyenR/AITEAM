from __future__ import annotations

import sys
from typing import Any, Dict, Optional, Sequence, Union


def _erase_empty_enter_line() -> None:
    """Erase the blank line left by pressing Enter on an empty input."""
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\033[1A\033[2K")
            sys.stdout.flush()
    except OSError:
        pass

from rich.console import Console

console = Console()
GLOBAL_BACK = "back"
GLOBAL_EXIT = "exit"


def _read_single_key_blocking() -> str:
    """Block until user presses a key; return that key. Discards everything
    else from the input buffer so characters don't leak to the next prompt.

    Returns "" on non-tty / unsupported terminals so callers can fall back
    to `input()` (e.g., during pytest runs)."""
    try:
        if not sys.stdin.isatty():
            return ""
    except (AttributeError, ValueError):
        return ""

    if sys.platform == "win32":
        try:
            import msvcrt

            ch = msvcrt.getwch()
            if ch in ("\x00", "\xe0"):
                try:
                    msvcrt.getwch()
                except OSError:
                    pass
                ch = "\r"
            while msvcrt.kbhit():
                try:
                    msvcrt.getwch()
                except OSError:
                    break
            sys.stdout.write("\n")
            sys.stdout.flush()
            return ch
        except (ImportError, OSError):
            return ""

    try:
        import select
        import termios
        import tty

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            while select.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\n")
        sys.stdout.flush()
        return ch
    except (ImportError, OSError, termios.error):  # type: ignore[name-defined]
        return ""


def wait_enter(message: str = "Nhấn Enter để tiếp tục...") -> None:
    try:
        console.print(message, end=" ")
    except (OSError, UnicodeError):
        pass
    try:
        ch = _read_single_key_blocking()
    except (OSError, KeyboardInterrupt):
        return
    if ch:
        return
    try:
        input("")
    except (EOFError, KeyboardInterrupt):
        pass


def normalize_global_command(raw: str) -> str:
    return (raw or "").strip().lower()


def ask_choice(
    prompt: Union[str, Any],
    choices: Sequence[str],
    *,
    default: Optional[str] = None,
    show_default: bool = True,
    allow_global: bool = True,
    number_map: Optional[Dict[str, str]] = None,
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
            _erase_empty_enter_line()
            continue
        if allow_global and raw in (GLOBAL_BACK, GLOBAL_EXIT):
            return raw
        if number_map and raw.isdigit():
            mapped = number_map.get(raw)
            if mapped is not None and mapped in allowed:
                return mapped
        if raw in allowed:
            return str(raw)
        console.print("[yellow]Invalid — try again.[/yellow]")


__all__ = ["ask_choice", "normalize_global_command", "wait_enter", "GLOBAL_BACK", "GLOBAL_EXIT"]
