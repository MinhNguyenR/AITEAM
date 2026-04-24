from __future__ import annotations

import time
from typing import Optional

from core.cli.pythonCli.nav import NavToMain
from core.cli.pythonCli.state import get_prompt_overrides, log_system_action
from core.cli.pythonCli.chrome.ui import console, clear_screen
from core.domain.prompts import ASK_MODE_SYSTEM_PROMPT
from core.storage import ask_history
from utils.input_validator import PromptInvalid, PromptTooLong, validate_user_prompt

from .ask_chat_manager import (
    _chat_name_from_prompt,
    _format_chat_header,
    _is_temp_chat_name,
    _new_chat_name,
    _pick_chat_on_ask_entry,
)
from .ask_history_renderer import (
    _ask_input_with_header,
    _print_message_panel,
    _render_loaded_history,
    ask_command_hints,
    render_history_lines,
)
from .ask_model_selector import _ask_model, _chat_model_settings


def looks_like_code_intent(text: str) -> bool:
    t = text.lower()
    keys = ["write code", "implement", "fix bug", "create file", "sửa code", "viết code", "refactor", "repo", "pull request"]
    return any(k in t for k in keys)


_EXPLAIN_ONLY_SUFFIX = (
    "\n\n[Ngữ cảnh CLI] Người dùng đang ở Ask với ý định liên quan code/repo. "
    "Chỉ giải thích, gợi ý, hoặc pseudo-code; không tuyên bố đã sửa file, chạy lệnh, hay truy cập repo."
)


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
        console.print("[red]Không thể tạo chat active.[/red]")
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
    while True:
        active = ask_history.get_active_chat(store)
        if not active:
            default_name = _new_chat_name()
            ask_history.create_chat(store, default_name, mode="standard")
            ask_history.save_store(store)
            active = ask_history.get_active_chat(store)
        chat_name = active["name"]
        mode = active.get("mode", "standard")
        pending_msg = None
        if active.get("messages"):
            last = active["messages"][-1]
            if last.get("role") == "user":
                pending_msg = last.get("content", "")
        if not pending_msg:
            pending_msg = _ask_input_with_header(
                _format_chat_header(active), mode, compact=not first_you_prompt
            )
            first_you_prompt = False
        text = pending_msg.strip()
        if not text:
            continue
        try:
            text = validate_user_prompt(text)
        except PromptTooLong as _e:
            console.print(f"[yellow]Tin nhắn quá dài ({len(pending_msg.strip()):,} ký tự). Tối đa 32,000 ký tự.[/yellow]")
            continue
        except PromptInvalid as _e:
            console.print(f"[yellow]Tin nhắn không hợp lệ: {_e}[/yellow]")
            continue
        tl = text.lower()
        if tl == "exit":
            ask_history.save_store(store)
            raise NavToMain
        if tl == "back":
            log_system_action("ask.back", chat_name)
            ask_history.save_store(store)
            return
        if text.lower() == "ask thinking":
            if mode == "thinking":
                console.print("[yellow]Đang là mode thinking.[/yellow]")
                time.sleep(3)
                continue
            ask_history.set_chat_mode(store, chat_name, "thinking")
            log_system_action("ask.mode.switch", f"{chat_name}:thinking")
            active = ask_history.get_active_chat(store) or active
            continue
        if text.lower() == "ask standard":
            if mode == "standard":
                console.print("[yellow]Đang là mode standard.[/yellow]")
                time.sleep(3)
                continue
            ask_history.set_chat_mode(store, chat_name, "standard")
            log_system_action("ask.mode.switch", f"{chat_name}:standard")
            active = ask_history.get_active_chat(store) or active
            continue
        if text.lower().startswith("ask "):
            console.print("[yellow]Trong chat: ask thinking | ask standard  ·  back | exit (về menu chính)[/yellow]")
            continue
        if looks_like_code_intent(text) and not explain_only:
            console.print("[yellow]Nếu muốn tạo/sửa file trong repo, vui lòng chuyển sang agent mode.[/yellow]")
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
        sys_content = _ask_system_prompt + (_EXPLAIN_ONLY_SUFFIX if explain_only else "")
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
            _last_replied_msg = text
            first_you_prompt = False
        except (OSError, RuntimeError, ValueError) as e:
            console.print(f"[red]Ask mode error: {e}[/red]")
            ask_history.save_store(store)


__all__ = ["run_ask_mode", "looks_like_code_intent", "ask_command_hints", "render_history_lines"]
