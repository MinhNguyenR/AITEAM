from __future__ import annotations

import sys
from typing import Any, Dict, Optional, Sequence, Union

from rich.console import Console
from core.cli.python_cli.i18n import t

# Try to import prompt_toolkit
try:
    from prompt_toolkit import prompt as pt_prompt
except ImportError:
    pt_prompt = None

console = Console()
GLOBAL_BACK = "back"
GLOBAL_EXIT = "exit"

def _erase_empty_enter_line() -> None:
    """Erase the blank line left by pressing Enter on an empty input."""
    try:
        if sys.stdout.isatty():
            sys.stdout.write("\033[1A\033[2K")
            sys.stdout.flush()
    except OSError:
        pass

def normalize_global_command(raw: str) -> str:
    r = (raw or "").strip().lower()
    # Normalize slash commands for backward compatibility
    if r == "/back": return GLOBAL_BACK
    if r == "/exit": return GLOBAL_EXIT
    return r

def wait_enter(message: Optional[str] = None) -> None:
    msg = message if message is not None else t("ui.wait_enter")
    try:
        console.print(msg, end=" ")
    except (OSError, UnicodeError):
        pass
    try:
        if pt_prompt:
            pt_prompt("")
        else:
            input("")
    except (EOFError, KeyboardInterrupt):
        pass

def ask_choice(
    prompt: Union[str, Any],
    choices: Sequence[str],
    *,
    default: Optional[str] = None,
    show_default: bool = True,
    allow_global: bool = True,
    number_map: Optional[Dict[str, str]] = None,
    context: str = "main",
    header_ansi: Optional[str] = None,
    **kwargs: Any,
) -> str:
    allowed = [str(c) for c in choices]
    if not allowed:
        raise ValueError("ask_choice requires at least one choice")
    
    d = str(default if default is not None else allowed[0])
    
    # Prepare completer
    completer = None
    if pt_prompt:
        try:
            from core.cli.python_cli.ui.autocomplete import ChoiceCompleter
            completer = ChoiceCompleter(context=context)
        except ImportError:
            pass

    while True:
        from rich.markup import escape as _esc
        suffix = f" [dim]\[[/dim][bold]{_esc(d)}[/bold][dim]][/dim]" if show_default and d else ""
        prompt_text = f"{prompt}{suffix} "
        
        try:
            if pt_prompt:
                from core.cli.python_cli.ui.palette_app import ask_with_palette
                from rich.text import Text
                raw_prompt = str(Text.from_markup(prompt_text))
                raw = ask_with_palette(raw_prompt, context=context, default=d, header_ansi=header_ansi)
            else:
                console.print(prompt_text, end="")
                raw = input()
        except (KeyboardInterrupt, EOFError):
            return GLOBAL_BACK

        raw = normalize_global_command(raw)
        if not raw:
            if default:
                return d
            _erase_empty_enter_line()
            continue
            
        if allow_global and raw in (GLOBAL_BACK, GLOBAL_EXIT):
            return raw
            
        # Also check for slashed versions in allowed
        if raw in allowed:
            return raw
        
        # Strip leading slash if user typed /command but only command is in allowed
        stripped = raw[1:] if raw.startswith('/') else raw
        if stripped in allowed:
            return stripped

        if number_map and raw.isdigit():
            mapped = number_map.get(raw)
            if mapped is not None and mapped in allowed:
                return mapped
        
        console.print(f"[yellow]{t('ui.invalid_retry')}[/yellow]")

__all__ = ["ask_choice", "normalize_global_command", "wait_enter", "GLOBAL_BACK", "GLOBAL_EXIT"]
