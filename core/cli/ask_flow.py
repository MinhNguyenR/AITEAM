from __future__ import annotations

import importlib
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Literal, Optional

from openai import OpenAI
from rich.box import ROUNDED
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from core.cli.state import log_system_action
from core.cli.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_BLUE, SOFT_WHITE, console, clear_screen
from core.config import config
from core.prompts import ASK_MODE_SYSTEM_PROMPT
from utils import ask_history
from utils.budget_guard import ensure_dashboard_budget_available

try:
    _pt_module = importlib.import_module("prompt_toolkit")
    pt_prompt = getattr(_pt_module, "prompt", None)
except (ImportError, AttributeError):
    pt_prompt = None


def looks_like_code_intent(text: str) -> bool:
    t = text.lower()
    keys = ["write code", "implement", "fix bug", "create file", "sửa code", "viết code", "refactor", "repo", "pull request"]
    return any(k in t for k in keys)


_HISTORY_PREVIEW_MAX_CHARS = 180


def ask_command_hints(mode: str) -> str:
    base = "ask thinking" if mode == "standard" else "ask standard"
    return f"{base}  ·  back thoát Ask  ·  exit về menu chính"


def render_history_lines(chat: Dict, limit: int = 12) -> List[str]:
    lines: List[str] = []
    messages = chat.get("messages", [])
    for m in messages[-limit:]:
        role = m.get("role", "user")
        label = "You" if role == "user" else "Assistant"
        content = (m.get("content", "") or "").strip()
        if len(content) > _HISTORY_PREVIEW_MAX_CHARS:
            content = content[: _HISTORY_PREVIEW_MAX_CHARS - 3] + "..."
        lines.append(f"{label}: {content}")
    return lines


def _chat_model_settings(mode: str) -> tuple[str, int, float, float]:
    worker_id = "CHAT_MODEL_THINKING" if mode == "thinking" else "CHAT_MODEL_STANDARD"
    cfg = config.get_worker(worker_id) or {}
    model = str(cfg.get("model") or (config.ASK_CHAT_THINKING_MODEL if mode == "thinking" else config.ASK_CHAT_STANDARD_MODEL))
    max_tokens = int(cfg.get("max_tokens") or 1200)
    temperature = float(cfg.get("temperature") if cfg.get("temperature") is not None else 1.2)
    top_p = float(cfg.get("top_p") if cfg.get("top_p") is not None else 0.95)
    return model, max_tokens, temperature, top_p


def _ask_model(mode: str, messages: list[dict]) -> str:
    model, max_tokens, temperature, top_p = _chat_model_settings(mode)
    ensure_dashboard_budget_available()
    client = OpenAI(api_key=config.api_key, base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"))
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )
    content = (resp.choices[0].message.content or "").strip()
    usage = getattr(resp, "usage", None)
    prompt_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tok = int(getattr(usage, "completion_tokens", 0) or 0)
    if prompt_tok or completion_tok:
        try:
            from utils.tracker import append_usage_log, compute_cost_usd

            event = {
                "agent": "Ask",
                "model": model,
                "prompt_tokens": prompt_tok,
                "completion_tokens": completion_tok,
                "total_tokens": prompt_tok + completion_tok,
            }
            event["cost_usd"] = compute_cost_usd(event)
            append_usage_log(event)
        except (OSError, ValueError) as e:
            log_system_action("ask.usage_log_skipped", str(e))
    log_system_action("ask.response", f"model={model} chars={len(content)} token_limit={max_tokens}")
    return content


def _new_chat_name() -> str:
    return f"new-chat-{datetime.now().strftime('%Y%m%d-%H%M')}"


def _is_temp_chat_name(name: str) -> bool:
    n = (name or "").strip().lower()
    return n.startswith("chat-") or n.startswith("new-chat-")


def _unique_chat_name(store: dict, base_name: str) -> str:
    existing = {str(item.get("name", "")).lower() for item in ask_history.list_chat_records(store, sort_by="updated_desc")}
    if base_name.lower() not in existing:
        return base_name
    idx = 2
    while f"{base_name}-{idx}".lower() in existing:
        idx += 1
    return f"{base_name}-{idx}"


def _chat_name_from_prompt(store: dict, prompt: str) -> str:
    text = re.sub(r"\s+", " ", (prompt or "").strip())
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip(" -_")
    if not text:
        return _new_chat_name()
    words = text.split()
    return _unique_chat_name(store, " ".join(words[:6])[:40].strip() or _new_chat_name())


def _format_chat_header(chat: dict) -> str:
    mode = chat.get("mode", "standard")
    model, _, _, _ = _chat_model_settings(mode)
    return f"{chat.get('name', 'chat')} mode={mode} model={model}"


def _print_message_panel(index: int, role: str, content: str, *, max_chars: int = 0) -> None:
    label = "You" if role == "user" else "Assistant"
    style = PASTEL_CYAN if role == "user" else SOFT_WHITE
    body = (content or "").strip()
    if max_chars > 0 and len(body) > max_chars:
        body = body[: max_chars - 3] + "..."
    if not body:
        body = "(empty)"
    inner = f"[{style}]{label}:[/{style}]\n{body}"
    console.print(
        Panel(
            inner,
            title=f"#{index}",
            title_align="right",
            border_style=PASTEL_BLUE,
            box=ROUNDED,
            padding=(0, 1),
        )
    )


def _render_loaded_history(chat: dict, limit: int = 12) -> None:
    messages = list(chat.get("messages") or [])
    if not messages:
        return
    console.print("[dim]Lịch sử gần nhất (xem trước):[/dim]")
    tail = messages[-limit:]
    base = len(messages) - len(tail) + 1
    for j, m in enumerate(tail):
        idx = base + j
        role = m.get("role", "user")
        if role not in ("user", "assistant"):
            continue
        _print_message_panel(idx, role, m.get("content", ""), max_chars=_HISTORY_PREVIEW_MAX_CHARS)
    console.print()


def _ask_input_with_header(header: str, mode: str, *, compact: bool = False) -> str:
    commands = ask_command_hints(mode)
    if compact:
        if pt_prompt:
            return pt_prompt(f"{commands}\nYOU> ")
        console.print(commands)
        return Prompt.ask("YOU>")
    if pt_prompt:
        return pt_prompt(f"{header}\n{commands}\nYOU> ")
    console.print(f"[bold cyan]{header}[/bold cyan]")
    console.print(commands)
    return Prompt.ask("YOU>")


def _pick_chat_on_ask_entry(store: dict, force_new_chat: bool = False) -> Optional[Literal["back"]]:
    if force_new_chat:
        new_name = _new_chat_name()
        ask_history.create_chat(store, new_name, mode="standard")
        log_system_action("ask.chat.create", new_name)
        return None
    while True:
        chats = ask_history.list_chat_records(store, sort_by="updated_desc")
        if not chats:
            new_name = _new_chat_name()
            ask_history.create_chat(store, new_name, mode="standard")
            log_system_action("ask.chat.create", new_name)
            return None
        table = Table(title="Danh sách hội thoại Ask", box=ROUNDED, border_style=PASTEL_BLUE, expand=True)
        table.add_column("Hội thoại", style="white", no_wrap=False)
        for idx, item in enumerate(chats, start=1):
            updated = item.get("updated_at", "")[:16].replace("T", " ")
            table.add_row(
                f"[bold cyan]{idx}.[/bold cyan] [bold]{item['name']}[/bold]  "
                f"[dim]· {item.get('mode', 'standard')} · {item.get('message_count', 0)} tin · {updated}[/dim]"
            )
        console.print(table)
        console.print(
            "[dim]Số / tên chat | ask create | ask rename … | ask delete … | back (hủy) | exit (về menu chính)[/dim]"
        )
        raw = Prompt.ask("Chọn hội thoại hoặc nhập lệnh", default="1").strip()
        lowered = raw.lower()
        if lowered == "exit":
            return "back"
        if lowered == "back":
            return "back"
        if raw.isdigit():
            pos = int(raw)
            if 1 <= pos <= len(chats):
                name = chats[pos - 1]["name"]
                ask_history.join_chat(store, name)
                log_system_action("ask.chat.join", name)
                return None
            console.print("[yellow]Số hội thoại không hợp lệ.[/yellow]")
            continue
        if lowered == "ask create":
            new_name = _new_chat_name()
            ask_history.create_chat(store, new_name, mode="standard")
            log_system_action("ask.chat.create", new_name)
            return None
        if lowered.startswith("ask rename "):
            payload = raw[11:].strip()
            if " - " not in payload:
                console.print("[yellow]Cú pháp: ask rename <ten_cu> - <ten_moi>[/yellow]")
                continue
            old_name, new_name = [x.strip() for x in payload.split(" - ", 1)]
            if old_name.isdigit():
                pos = int(old_name)
                if 1 <= pos <= len(chats):
                    old_name = chats[pos - 1]["name"]
            if ask_history.rename_chat(store, old_name, new_name):
                log_system_action("ask.chat.rename", f"{old_name}->{new_name}")
            else:
                console.print("[yellow]Rename thất bại.[/yellow]")
            continue
        if lowered.startswith("ask delete "):
            target = raw[11:].strip()
            if target.isdigit():
                pos = int(target)
                if 1 <= pos <= len(chats):
                    target = chats[pos - 1]["name"]
            if ask_history.delete_chat(store, target):
                log_system_action("ask.chat.delete", target)
                console.print(f"[dim]Đã xóa: {target}[/dim]")
            else:
                console.print("[yellow]Delete thất bại.[/yellow]")
            continue
        for c in chats:
            if c["name"] == raw or str(c["name"]).lower() == lowered:
                ask_history.join_chat(store, c["name"])
                log_system_action("ask.chat.join", c["name"])
                return None
        console.print("[yellow]Lệnh không hợp lệ trong màn danh sách.[/yellow]")


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
        tl = text.lower()
        if tl == "exit":
            ask_history.save_store(store)
            return
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
        try:
            from core.cli.state import get_prompt_overrides

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
        except (OSError, RuntimeError, ValueError) as e:
            console.print(f"[red]Ask mode error: {e}[/red]")
            ask_history.save_store(store)


__all__ = ["run_ask_mode", "looks_like_code_intent", "ask_command_hints", "render_history_lines"]
