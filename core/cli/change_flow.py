"""
change_flow.py — CLI for viewing and overriding model/prompt per role.
Commands:
  change          -> list all roles with numbers
  change <n>      -> detail + sub-commands for role n
  change to <id>  -> (inside detail) set model override
  change prompt   -> (inside detail) set prompt override
  change reset    -> (inside detail) reset model + prompt override
"""
from __future__ import annotations

import textwrap
from typing import Optional

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.markup import escape
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.console import Group
from rich.table import Table
from rich.text import Text

from core.cli.state import (
    get_model_overrides,
    get_prompt_overrides,
    reset_all_role_overrides,
    set_model_override,
    set_prompt_override,
)
from core.cli.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, SOFT_WHITE, clear_screen, console, print_header
from core.config import config
from core.config.pricing import fetch_model_detail


def _indexed_workers() -> list[dict]:
    return list(config.list_workers())


def _score_bar(val: float, width: int = 28) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "—"
    if v > 1.0 + 1e-9:
        x = max(0.0, min(1.0, v / 100.0)) if v <= 100.0 else 1.0
    else:
        x = max(0.0, min(1.0, v))
    n = int(round(x * width))
    return f"{'#' * n}{'.' * (width - n)} {v:.4g}"


def _prompt_panel_content(has_prompt_override: bool, prompt_info: dict) -> Text | Group:
    """Rich-safe body: user override verbatim (escaped); else default System Prompt notice."""
    cw = console.size.width or 100
    wrap_w = max(56, min(cw - 8, 110))
    if has_prompt_override and (prompt_info.get("prompt") or "").strip():
        raw = str(prompt_info["prompt"])
        wrapped = textwrap.fill(raw, width=wrap_w, replace_whitespace=False, drop_whitespace=False)
        main = Text.from_markup(escape(wrapped))
        ts = prompt_info.get("updated_at")
        if ts:
            foot = Text.from_markup(f"[dim]Cập nhật: {escape(str(ts)[:19])}[/dim]")
            return Group(main, Text(""), foot)
        return main
    return Text.from_markup(
        "[bold]System Prompt[/bold] [dim](mặc định)[/dim]\n\n"
        "Đang dùng prompt gốc của framework — [dim]nội dung không hiển thị để bảo vệ cấu hình nội bộ[/dim].\n\n"
        "Gõ [bold]change prompt[/bold] hoặc [bold]prompt[/bold] để nhập prompt tùy chỉnh; "
        "sau khi lưu, toàn bộ nội dung bạn nhập sẽ hiển thị tại đây."
    )


def _price_str(pricing: dict) -> str:
    inp = pricing.get("input", 0.0)
    out = pricing.get("output", 0.0)
    if inp == 0 and out == 0:
        return "N/A"
    return f"${inp:.2f}/${out:.2f}"


def pick_role_key_from_indexed_workers(workers: list[dict]) -> Optional[str]:
    """Prompt for role index after the registry table is already shown (no clear_screen)."""
    if not workers:
        return None
    console.print()
    console.print(
        f"[{PASTEL_LAVENDER}]Nhập số 1–{len(workers)} để chi tiết / đổi model hoặc prompt | "
        f"back về menu | exit về menu chính[/{PASTEL_LAVENDER}]"
    )
    try:
        raw = Prompt.ask(f"[bold {PASTEL_CYAN}]Chọn[/bold {PASTEL_CYAN}]", default="back").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return None
    if raw in ("back", "b", ""):
        return None
    if raw == "exit":
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(workers):
            return workers[idx]["id"]
    return None


def show_change_list() -> Optional[str]:
    """Display indexed role list; return role_key selected or None."""
    clear_screen()
    print_header("🔧 MODEL REGISTRY — CHANGE")
    workers = _indexed_workers()
    table = Table(box=ROUNDED, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True), border_style=PASTEL_BLUE, padding=(0, 1))
    table.add_column("#", style="dim", width=4)
    table.add_column("Role Key", style=Style(color=PASTEL_CYAN), width=20)
    table.add_column("Role", style=Style(color=SOFT_WHITE), width=26)
    table.add_column("Model", style="white", width=30)
    table.add_column("Active", justify="center", width=8)
    table.add_column("Price in/out /1M", width=20)
    table.add_column("Override", justify="center", width=10)
    for i, w in enumerate(workers, 1):
        active_icon = "[green]✅[/green]" if w.get("active", True) else "[red]❌[/red]"
        override_icon = "[yellow]✏[/yellow]" if w.get("is_overridden") else "[dim]—[/dim]"
        prompt_icon = " [cyan]P[/cyan]" if w.get("prompt_status") == "overridden" else ""
        table.add_row(
            str(i),
            w["id"],
            w["role"],
            w["model"],
            active_icon,
            _price_str(w.get("pricing", {})),
            override_icon + prompt_icon,
        )
    console.print(table)
    console.print()
    console.print(f"[dim]Override[/dim]: ✏ model overridden  [cyan]P[/cyan] prompt overridden")
    console.print()
    console.print(f"[{PASTEL_LAVENDER}]Commands:[/{PASTEL_LAVENDER}] <số thứ tự> | back")
    try:
        raw = Prompt.ask(f"[bold {PASTEL_CYAN}]Chọn role[/bold {PASTEL_CYAN}]", default="back").strip().lower()
    except (KeyboardInterrupt, EOFError):
        return None
    if raw in ("back", "b", ""):
        return None
    if raw == "exit":
        return None
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(workers):
            return workers[idx]["id"]
    return None


def show_role_detail(role_key: str) -> None:
    """Show detailed info for a role and handle sub-commands in a loop."""
    while True:
        clear_screen()
        workers = _indexed_workers()
        w = next((x for x in workers if x["id"] == role_key), None)
        if not w:
            console.print(f"[red]Không tìm thấy role: {role_key}[/red]")
            return
        model_overrides = get_model_overrides()
        prompt_overrides = get_prompt_overrides()
        is_overridden = role_key.upper() in model_overrides
        has_prompt_override = role_key.upper() in prompt_overrides
        prompt_info = prompt_overrides.get(role_key.upper(), {})

        # Build main info table
        info = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
        info.add_column("K", style=Style(color=PASTEL_CYAN), width=18)
        info.add_column("V", style="white", width=50)
        info.add_row("Role Key", f"[bold]{role_key}[/bold]")
        info.add_row("Role", w["role"])
        info.add_row("Tier", w.get("tier", "—"))
        info.add_row("Priority", str(w.get("priority", "—")))
        info.add_row("Active", "[green]✅ Yes[/green]" if w.get("active", True) else "[red]❌ No[/red]")
        info.add_row("Model (effective)", f"[bold]{w['model']}[/bold]")
        if is_overridden:
            info.add_row("Default model", f"[dim]{w.get('default_model', '—')}[/dim]")
            info.add_row("Model override", "[yellow]✏ Active[/yellow]")
        pricing = w.get("pricing", {})
        info.add_row("Price input /1M", f"${pricing.get('input', 0.0):.4f}" if pricing else "N/A")
        info.add_row("Price output /1M", f"${pricing.get('output', 0.0):.4f}" if pricing else "N/A")
        info.add_row("Temperature", str(w.get("temperature", "—")))
        info.add_row("Top P", str(w.get("top_p", "—")))
        info.add_row("Max Tokens", str(w.get("max_tokens", "—")))

        console.print(Panel(info, title=f"[bold {PASTEL_CYAN}]🤖 {role_key}[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))

        prompt_title = (
            "Prompt tùy chỉnh (nội dung bạn đã nhập)"
            if has_prompt_override and (prompt_info.get("prompt") or "").strip()
            else "Prompt"
        )
        console.print(
            Panel(
                _prompt_panel_content(has_prompt_override, prompt_info),
                title=f"[bold {PASTEL_CYAN}]{prompt_title}[/bold {PASTEL_CYAN}]",
                border_style=PASTEL_CYAN,
                box=ROUNDED,
                padding=(1, 2),
            )
        )

        # Fetch OpenRouter metadata live
        console.print(f"[dim]Đang tải metadata từ OpenRouter...[/dim]", end="\r")
        meta = fetch_model_detail(config.api_key, w["model"]) or {}
        dfull = str(meta.get("description") or "").strip()
        meta_table = Table(box=ROUNDED, show_header=False, border_style=PASTEL_LAVENDER, padding=(0, 2))
        meta_table.add_column("K", style=Style(color=PASTEL_LAVENDER), width=20)
        meta_table.add_column("V", style="white", width=46)
        meta_table.add_row("Name", meta.get("name") or "N/A")
        meta_table.add_row("Description", "[dim](panel mô tả đầy đủ bên dưới)[/dim]" if dfull else "N/A")
        meta_table.add_row("Context length", str(meta.get("context_length") or "N/A"))
        top = meta.get("top_provider") or {}
        meta_table.add_row("Max completion", str(meta.get("max_completion") or top.get("max_completion_tokens") or "N/A"))
        meta_table.add_row("Moderation", str(meta.get("moderation") if meta.get("moderation") is not None else top.get("is_moderated", "N/A")))
        arch = meta.get("architecture")
        if arch is not None and str(arch).strip():
            astr = str(arch)
            meta_table.add_row("Architecture", astr[:320] + ("…" if len(astr) > 320 else ""))
        ek = meta.get("extra_keys") or []
        if ek:
            meta_table.add_row("Extra keys", ", ".join(str(x) for x in ek[:12]) + ("…" if len(ek) > 12 else ""))
        console.print(Panel(meta_table, title=f"[{PASTEL_LAVENDER}]🌐 OpenRouter Metadata[/{PASTEL_LAVENDER}]", border_style=PASTEL_LAVENDER, box=ROUNDED))
        if dfull:
            console.print(
                Panel(
                    Markdown(dfull),
                    title=f"[bold {PASTEL_CYAN}]Mô tả (OpenRouter)[/bold {PASTEL_CYAN}]",
                    border_style=PASTEL_BLUE,
                    box=ROUNDED,
                    padding=(1, 2),
                )
            )
        bench = meta.get("benchmark_scores") or {}
        if bench:
            bt = Table(box=ROUNDED, title="Benchmark / metrics (động)", border_style=PASTEL_LAVENDER)
            bt.add_column("Metric", style=PASTEL_CYAN, overflow="fold")
            bt.add_column("Val", justify="right", width=10)
            bt.add_column("Bar", width=34)
            for k, v in sorted(bench.items(), key=lambda x: str(x[0]))[:48]:
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                bt.add_row(str(k)[:44], f"{fv:.4f}", _score_bar(fv))
            console.print(Panel(bt, border_style=PASTEL_LAVENDER, box=ROUNDED))
        else:
            console.print(
                "[dim]OpenRouter không cung cấp benchmark số cho model này (hoặc không nhận diện được trường).[/dim]"
            )
        console.print()

        console.print(
            f"[{PASTEL_LAVENDER}]Commands:[/{PASTEL_LAVENDER}] "
            f"[bold]change to <model_id>[/bold] | [bold]change prompt[/bold] | [bold]change reset[/bold] | [bold]back[/bold]"
        )
        try:
            cmd = Prompt.ask(f"[bold {PASTEL_CYAN}]>{role_key}[/bold {PASTEL_CYAN}]", default="back").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if cmd.lower() in ("back", "exit", "b", ""):
            return

        if cmd.lower().startswith("change to "):
            new_model = cmd[len("change to "):].strip()
            if not new_model:
                console.print("[yellow]⚠ Vui lòng nhập model id (vd: openai/gpt-4o).[/yellow]")
                input("[dim]Enter để tiếp tục...[/dim]")
                continue
            set_model_override(role_key.upper(), new_model)
            console.print(f"[green]✓ Đã đổi model của {role_key} → {new_model}[/green]")
            input("[dim]Enter để reload...[/dim]")
            continue

        if cmd.lower() in ("change prompt", "prompt"):
            console.print()
            console.print(f"[{PASTEL_CYAN}]Nhập prompt mới cho {role_key}[/{PASTEL_CYAN}]")
            console.print("[dim](Prompt gốc không được hiển thị. Để trống = hủy)[/dim]")
            try:
                new_prompt = Prompt.ask("Prompt").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not new_prompt:
                console.print("[dim]Đã hủy — prompt không thay đổi.[/dim]")
                input("[dim]Enter để tiếp tục...[/dim]")
                continue
            set_prompt_override(role_key.upper(), new_prompt)
            console.print(f"[green]✓ Đã lưu prompt override cho {role_key}.[/green]")
            input("[dim]Enter để reload...[/dim]")
            continue

        if cmd.lower() in ("change reset", "reset"):
            reset_all_role_overrides(role_key.upper())
            console.print(f"[green]✓ Đã reset model và prompt về mặc định cho {role_key}.[/green]")
            input("[dim]Enter để reload...[/dim]")
            continue

        console.print(f"[yellow]Lệnh không nhận ra: {cmd}[/yellow]")
        input("[dim]Enter để tiếp tục...[/dim]")


def run_change_flow() -> None:
    """Entry point: show list → detail loop."""
    while True:
        role_key = show_change_list()
        if role_key is None:
            return
        show_role_detail(role_key)


__all__ = ["run_change_flow", "show_change_list", "show_role_detail", "pick_role_key_from_indexed_workers"]
