from __future__ import annotations

import re
from datetime import datetime
from typing import Literal, Optional

from rich.box import ROUNDED
from rich.prompt import Prompt
from rich.table import Table

from core.cli.python_cli.ui.ui import PASTEL_BLUE, clear_screen, console
from core.cli.python_cli.shell.nav import NavToMain
from core.app_state import log_system_action
from core.storage import ask_history
from core.cli.python_cli.i18n import t

from .history_renderer import _ask_input_with_header
from .model_selector import _chat_model_settings


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
    return f"{chat.get('name', t('ask.chat_col'))} mode={mode} model={model}"


def _resolve_chat_name(token: str, chats: list) -> str | None:
    tok = (token or "").strip()
    if tok.isdigit():
        pos = int(tok)
        if 1 <= pos <= len(chats):
            return str(chats[pos - 1]["name"])
    return tok if tok else None


def _parse_index_list(s: str, nchats: int) -> list[int]:
    """Parse 'N' (single) or 'N M' (range N to M inclusive) into sorted index list."""
    tokens = [p for p in re.split(r"[\s,;]+", s.strip()) if p]
    if len(tokens) == 1 and tokens[0].isdigit():
        i = int(tokens[0])
        return [i] if 1 <= i <= nchats else []
    if len(tokens) == 2 and tokens[0].isdigit() and tokens[1].isdigit():
        a, b = int(tokens[0]), int(tokens[1])
        lo, hi = min(a, b), max(a, b)
        return [i for i in range(lo, hi + 1) if 1 <= i <= nchats]
    out: list[int] = []
    for p in tokens:
        if p.isdigit():
            i = int(p)
            if 1 <= i <= nchats:
                out.append(i)
    return sorted(set(out))


def _pick_chat_on_ask_entry(store: dict, force_new_chat: bool = False) -> Optional[Literal["back"]]:
    if force_new_chat:
        new_name = _new_chat_name()
        ask_history.create_chat(store, new_name, mode="standard")
        log_system_action("ask.chat.create", new_name)
        return None

    page = 0
    page_size = 18

    while True:
        chats = ask_history.list_chat_records(store, sort_by="updated_desc")
        if not chats:
            new_name = _new_chat_name()
            ask_history.create_chat(store, new_name, mode="standard")
            log_system_action("ask.chat.create", new_name)
            return None

        total_pages = (len(chats) + page_size - 1) // page_size
        page = max(0, min(page, total_pages - 1))

        start_idx = page * page_size
        end_idx = min(start_idx + page_size, len(chats))
        page_chats = chats[start_idx:end_idx]

        # Capture the UI to ANSI so we can push palette to bottom
        import shutil
        from io import StringIO
        from rich.console import Console as RichConsole
        from core.cli.python_cli.ui.ui import PASTEL_CYAN

        width = shutil.get_terminal_size((120, 30)).columns
        sio = StringIO()
        cap = RichConsole(file=sio, force_terminal=True, width=width, no_color=False, highlight=False, markup=True)

        title = f"{t('ask.chat_list_title')} [dim]({page+1}/{total_pages})[/dim]"
        table = Table(title=title, box=ROUNDED, border_style=PASTEL_BLUE, expand=True)
        table.add_column(t("ask.chat_col"), style="white", no_wrap=False)

        for idx_in_page, item in enumerate(page_chats, start=start_idx + 1):
            updated = item.get("updated_at", "")[:16].replace("T", " ")
            table.add_row(
                f"[bold cyan]{idx_in_page}.[/bold cyan] [bold]{item['name']}[/bold]  "
                f"[dim]. {item.get('mode', 'standard')} . {t('ask.msg_count').format(n=item.get('message_count', 0))} . {updated}[/dim]"
            )
        cap.print(table)
        ansi_header = sio.getvalue()

        from core.cli.python_cli.ui.palette_app import ask_with_palette
        # Removed prompt text for minimalist look
        raw = ask_with_palette("", context="ask_chat",
                               default="", header_ansi=ansi_header).strip()
        if not raw:
            continue
        lowered = raw.lower()
        if lowered == "/exit":
            raise NavToMain
        if lowered == "/back":
            return "back"

        if lowered == "/next":
            if page < total_pages - 1:
                page += 1
            continue
        if lowered == "/prev":
            if page > 0:
                page -= 1
            continue

        if lowered == "/create":
            new_name = _new_chat_name()
            ask_history.create_chat(store, new_name, mode="standard")
            log_system_action("ask.chat.create", new_name)
            return None
        if lowered == "/delete all":
            ask_history.delete_all_chats(store)
            log_system_action("ask.chat.delete_all", "1")
            continue
        if lowered.startswith("/delete "):
            payload = raw.split(None, 1)[1] if " " in raw else ""
            if payload.lower() == "all":
                ask_history.delete_all_chats(store)
                log_system_action("ask.chat.delete_all", "1")
                continue
            idxs = _parse_index_list(payload, len(chats))
            if not idxs:
                continue
            names = [chats[i - 1]["name"] for i in idxs]
            num_deleted = ask_history.delete_chats_bulk(store, names)
            log_system_action("ask.chat.delete_bulk", str(num_deleted))
            continue
        if lowered.startswith("/rename ") and len(raw.split()) >= 3:
            parts = raw.split(None, 2)
            old_tok, new_name = parts[1], parts[2].strip()
            old_name = _resolve_chat_name(old_tok, chats)
            if old_name and ask_history.rename_chat(store, old_name, new_name):
                log_system_action("ask.chat.rename", f"{old_name}->{new_name}")
            continue

        if lowered.startswith("/open "):
            payload = raw.split(None, 1)[1] if " " in raw else ""
            if payload.isdigit():
                pos = int(payload)
                if 1 <= pos <= len(chats):
                    name = chats[pos - 1]["name"]
                    ask_history.join_chat(store, name)
                    log_system_action("ask.chat.join", name)
                    return None
            continue

        # Exact name match still allowed
        for c in chats:
            if c["name"] == raw or str(c["name"]).lower() == lowered:
                ask_history.join_chat(store, c["name"])
                log_system_action("ask.chat.join", c["name"])
                return None


__all__ = ["_pick_chat_on_ask_entry"]
