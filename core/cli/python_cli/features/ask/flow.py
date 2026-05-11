from __future__ import annotations

import shutil
import time
from typing import Optional
from io import StringIO
from rich.console import Console as RichConsole
from rich.markdown import Markdown
from rich.panel import Panel
from rich.box import ROUNDED

from core.cli.python_cli.shell.nav import NavToMain
from core.app_state import get_prompt_overrides, log_system_action
from core.cli.python_cli.ui.ui import console, clear_screen, PASTEL_BLUE, PASTEL_LAVENDER
from core.cli.python_cli.ui.palette_app import ask_with_palette
from core.domain.prompts import ASK_MODE_SYSTEM_PROMPT
from core.storage import ask_history
from core.cli.python_cli.i18n import t
from utils.input_validator import PromptInvalid, PromptTooLong, validate_user_prompt

from .chat_manager import (
    _chat_name_from_prompt,
    _format_chat_header,
    _is_temp_chat_name,
    _new_chat_name,
    _pick_chat_on_ask_entry,
)
from .model_selector import _chat_model_settings
from .history_renderer import (
    _ask_input_with_header,
    _print_message_panel,
    _render_loaded_history,
    ask_command_hints,
    render_history_lines,
)
from .model_selector import _ask_model, _chat_model_settings


def looks_like_code_intent(text: str) -> bool:
    t_low = text.lower()
    keys = ["write code", "implement", "fix bug", "create file", "refactor", "repo", "pull request"]
    return any(k in t_low for k in keys)


def _explain_only_suffix() -> str:
    return t("ask.explain_suffix")


def run_ask_mode(
    prompt: str,
    force_new_chat: bool = False,
    *,
    skip_entry_pick: bool = False,
    explain_only: bool = False,
):
    log_system_action("ask.request", prompt[:200])
    clear_screen()
    store = ask_history.load_store()
    if not skip_entry_pick:
        pick = _pick_chat_on_ask_entry(store, force_new_chat=force_new_chat)
        if pick == "back":
            ask_history.save_store(store)
            return
    active = ask_history.get_active_chat(store)
    if not active:
        console.print(f"[red]{t('context.new_chat_err')}[/red]")
        return
    _render_loaded_history(active)
    if prompt.strip():
        _, max_tokens, _, _ = _chat_model_settings(active.get("mode", "standard"))
        ask_history.append_message(store, active["name"], "user", prompt.strip(), token_limit=max_tokens)
        active = ask_history.get_active_chat(store) or active
        if _is_temp_chat_name(active.get("name", "")):
            new_name = _chat_name_from_prompt(store, prompt)
            if ask_history.rename_chat(store, active["name"], new_name):
                log_system_action("ask.chat.rename", f"{active['name']}->{new_name}")
                active = ask_history.get_active_chat(store) or active
        _print_message_panel(len(active.get("messages") or []), "user", prompt.strip())

    ask_history.save_store(store)

    first_you_prompt = True
    _last_replied_msg: str | None = None
    _last_rendered_msg_idx = 0

    active = ask_history.get_active_chat(store)
    if not active:
        default_name = _new_chat_name()
        ask_history.create_chat(store, default_name, mode="standard")
        ask_history.save_store(store)
        active = ask_history.get_active_chat(store)

    chat_name = active["name"]
    mode = active.get("mode", "standard")

    # Print initial header and history once
    clear_screen()
    model_name, _, _, _ = _chat_model_settings(mode)
    width = shutil.get_terminal_size((120, 30)).columns
    console.print(f"\n[dim]{'-' * ((width-20)//2)} {t('ask.history_rule')} {'-' * ((width-20)//2)}[/dim]")
    mode_label = f"[bold white on blue] {mode.upper()} [/bold white on blue] [dim]({model_name})[/dim]"
    console.print(f" [bold cyan]{chat_name}[/bold cyan]  {mode_label}")
    console.print(f"[dim]{'-' * width}[/dim]\n")

    messages = active.get("messages", [])
    for idx, msg in enumerate(messages):
        _print_message_panel(idx + 1, msg.get("role", "user"), msg.get("content", ""))
    _last_rendered_msg_idx = len(messages)

    while True:
        active = ask_history.get_active_chat(store)
        if not active:
            break

        chat_name = active["name"]
        mode = active.get("mode", "standard")
        messages = active.get("messages", [])

        # Print any new messages that arrived
        while _last_rendered_msg_idx < len(messages):
            msg = messages[_last_rendered_msg_idx]
            _print_message_panel(_last_rendered_msg_idx + 1, msg.get("role", "user"), msg.get("content", ""))
            _last_rendered_msg_idx += 1

        ctx = "ask_session_thinking" if mode == "thinking" else "ask_session_standard"

        try:
            text = ask_with_palette("> ", context=ctx, compact=True).strip()

        except (KeyboardInterrupt, EOFError):
            break

        if not text:
            import time
            time.sleep(0.1) # Prevent spamming
            continue
        try:
            text = validate_user_prompt(text)
        except PromptTooLong as _e:
            console.print(f"[yellow]{t('ask.msg_too_long').format(n=len(text))}[/yellow]")
            continue
        except PromptInvalid as _e:
            console.print(f"[yellow]{t('ask.msg_invalid').format(e=_e)}[/yellow]")
            continue

        tl = text.lower()
        if tl == "/exit":
            ask_history.save_store(store)
            raise NavToMain
        if tl == "/back":
            log_system_action("ask.back", chat_name)
            ask_history.save_store(store)
            return
        if tl == "/thinking":
            if mode == "thinking":
                console.print(f"[yellow]{t('ask.mode_thinking')}[/yellow]")
                import time
                time.sleep(1)
                continue
            ask_history.set_chat_mode(store, chat_name, "thinking")
            log_system_action("ask.mode.switch", f"{chat_name}:thinking")
            active = ask_history.get_active_chat(store) or active
            model_name, _, _, _ = _chat_model_settings("thinking")
            console.print(f"\n[dim]--[/dim] [bold white on blue] THINKING [/bold white on blue] [dim]({model_name})[/dim]")
            console.print()
            continue
        if tl == "/standard":
            if mode == "standard":
                console.print(f"[yellow]{t('ask.mode_standard')}[/yellow]")
                import time
                time.sleep(1)
                continue
            ask_history.set_chat_mode(store, chat_name, "standard")
            log_system_action("ask.mode.switch", f"{chat_name}:standard")
            active = ask_history.get_active_chat(store) or active
            model_name, _, _, _ = _chat_model_settings("standard")
            console.print(f"\n[dim]--[/dim] [bold white on blue] STANDARD [/bold white on blue] [dim]({model_name})[/dim]")
            console.print()
            continue
        if looks_like_code_intent(text) and not explain_only:
            console.print(f"[yellow]{t('ask.agent_mode_hint')}[/yellow]")
            continue
        if text == _last_replied_msg:
            _last_replied_msg = None
            continue
        appended_user = False
        if not (
            active.get("messages")
            and active["messages"][-1].get("role") == "user"
            and active["messages"][-1].get("content") == text
        ):
            _, max_tokens, _, _ = _chat_model_settings(active.get("mode", "standard"))
            ask_history.append_message(store, chat_name, "user", text, token_limit=max_tokens)
            appended_user = True
        active = ask_history.get_active_chat(store) or active
        if appended_user and _is_temp_chat_name(active.get("name", "")):
            new_name = _chat_name_from_prompt(store, text)
            if ask_history.rename_chat(store, active["name"], new_name):
                log_system_action("ask.chat.rename", f"{active['name']}->{new_name}")
                active = ask_history.get_active_chat(store) or active
        if appended_user:
            _print_message_panel(len(active.get("messages") or []), "user", text)
            _last_rendered_msg_idx += 1
        model, max_tokens, _, _ = _chat_model_settings(active.get("mode", "standard"))
        _ask_system_prompt = ASK_MODE_SYSTEM_PROMPT
        _ask_role = "CHAT_MODEL_STANDARD"
        try:
            _ask_role = "CHAT_MODEL_THINKING" if active.get("mode") == "thinking" else "CHAT_MODEL_STANDARD"
            _overrides = get_prompt_overrides()
            if _ask_role in _overrides:
                _ask_system_prompt = _overrides[_ask_role]["prompt"]
        except (KeyError, TypeError, AttributeError):
            log_system_action("ask.prompt_override_invalid", _ask_role)
        sys_content = _ask_system_prompt + (_explain_only_suffix() if explain_only else "")
        model_messages = [{"role": "system", "content": sys_content}]
        for m in active.get("messages", [])[-20:]:
            role = m.get("role")
            if role in ("user", "assistant"):
                model_messages.append({"role": role, "content": m.get("content", "")})
        try:
            answer = _ask_model(active.get("mode", "standard"), model_messages)
            ask_history.append_message(store, chat_name, "assistant", answer, model=model, token_limit=max_tokens)
            ask_history.save_store(store)
            active_after = ask_history.get_active_chat(store) or active
            msg_n = len(active_after.get("messages") or [])
            _print_message_panel(msg_n, "assistant", answer or "")
            _last_rendered_msg_idx += 1
            _last_replied_msg = text
            first_you_prompt = False

            # Visual spacing before the next prompt
            console.print()
        except (OSError, RuntimeError, ValueError) as e:
            console.print(f"[red]{t('cmd.ask_error')}: {e}[/red]")
            ask_history.save_store(store)


__all__ = ["run_ask_mode", "looks_like_code_intent", "ask_command_hints", "render_history_lines"]
