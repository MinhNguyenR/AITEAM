from __future__ import annotations

import json

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table

from core.cli.python_cli.cli_prompt import wait_enter
from core.cli.python_cli.flows.change.helpers import indexed_workers, prompt_panel_content, score_bar
from core.cli.python_cli.nav import NavToMain
from core.cli.python_cli.state import (
    get_sampling_overrides,
    get_model_overrides,
    get_prompt_overrides,
    reset_all_role_overrides,
    reset_sampling_override,
    set_model_override,
    set_prompt_override,
    update_sampling_override,
)
from core.cli.python_cli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, clear_screen, console
from core.config import config
from core.config.pricing import fetch_model_detail

_EXTRA_KEY_HINTS: dict[str, str] = {
    "tools": "function/tool calling",
    "json_object": "structured JSON output",
    "json_schema": "JSON schema output",
    "vision": "image input",
    "audio": "audio input",
    "reasoning": "chain-of-thought reasoning",
    "streaming": "streaming responses",
    "function_calling": "function calling",
    "parallel_tool_calls": "parallel tool calls",
    "message_delta": "streaming deltas",
    "online": "web search / online",
}


def _format_architecture(arch: object) -> str:
    if isinstance(arch, dict):
        lines = []
        for k, v in arch.items():
            if v is None or v == "":
                continue
            label = str(k).replace("_", " ").title()
            lines.append(f"[{PASTEL_LAVENDER}]{label}:[/{PASTEL_LAVENDER}] {v}")
        return "\n".join(lines) if lines else str(arch)
    try:
        d = json.loads(str(arch))
        if isinstance(d, dict):
            return _format_architecture(d)
    except (json.JSONDecodeError, TypeError):
        pass
    return str(arch)


def _format_extra_keys(ek: list) -> str:
    lines = []
    for key in ek:
        hint = _EXTRA_KEY_HINTS.get(str(key), "")
        suffix = f"  [dim]— {hint}[/dim]" if hint else ""
        lines.append(f"• {key}{suffix}")
    return "\n".join(lines) if lines else ""


def show_role_detail(role_key: str) -> None:
    while True:
        clear_screen()
        workers = indexed_workers()
        w = next((x for x in workers if x["id"] == role_key), None)
        if not w:
            console.print(f"[red]Không tìm thấy role: {role_key}[/red]")
            return
        model_overrides = get_model_overrides()
        prompt_overrides = get_prompt_overrides()
        is_overridden = role_key.upper() in model_overrides
        has_prompt_override = role_key.upper() in prompt_overrides
        prompt_info = prompt_overrides.get(role_key.upper(), {})

        info = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
        info.add_column("K", style=Style(color=PASTEL_CYAN), width=18)
        info.add_column("V", style="white", width=50)
        info.add_row("Role Key", f"[bold]{role_key}[/bold]")
        info.add_row("Role", w["role"])
        raw_reason = w.get("reason", "")
        info.add_row("Reason", f"[dim]{raw_reason}[/dim]" if raw_reason else "[dim]—[/dim]")
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
        samp = get_sampling_overrides().get(role_key.upper(), {}) or {}
        temp_val = samp.get("temperature", w.get("temperature", "—"))
        topp_val = samp.get("top_p", w.get("top_p", "—"))
        maxt_val = samp.get("max_tokens", w.get("max_tokens", "—"))
        temp_tag = " [yellow]✏[/yellow]" if "temperature" in samp else ""
        topp_tag = " [yellow]✏[/yellow]" if "top_p" in samp else ""
        maxt_tag = " [yellow]✏[/yellow]" if "max_tokens" in samp else ""
        info.add_row("Temperature", f"{temp_val}{temp_tag}")
        info.add_row("Top P", f"{topp_val}{topp_tag}")
        info.add_row("Max Tokens", f"{maxt_val}{maxt_tag}")
        if samp:
            info.add_row("Sampling override", "[yellow]✏ Active[/yellow]")

        console.print(Panel(info, title=f"[bold {PASTEL_CYAN}]🤖 {role_key}[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))

        prompt_title = (
            "Prompt tùy chỉnh (nội dung bạn đã nhập)"
            if has_prompt_override and (prompt_info.get("prompt") or "").strip()
            else "Prompt"
        )
        console.print(
            Panel(
                prompt_panel_content(has_prompt_override, prompt_info),
                title=f"[bold {PASTEL_CYAN}]{prompt_title}[/bold {PASTEL_CYAN}]",
                border_style=PASTEL_CYAN,
                box=ROUNDED,
                padding=(1, 2),
            )
        )

        console.print("[dim]Đang tải metadata từ OpenRouter...[/dim]", end="\r")
        meta = fetch_model_detail(config.api_key, w["model"]) or {}
        dfull = str(meta.get("description") or "").strip()
        meta_table = Table(box=ROUNDED, show_header=False, border_style=PASTEL_LAVENDER, padding=(0, 2))
        meta_table.add_column("K", style=Style(color=PASTEL_LAVENDER), width=20)
        meta_table.add_column("V", style="white", overflow="fold")
        meta_table.add_row("Name", meta.get("name") or "N/A")
        meta_table.add_row("Description", "[dim](xem panel bên dưới)[/dim]" if dfull else "N/A")
        meta_table.add_row("Context length", str(meta.get("context_length") or "N/A"))
        top = meta.get("top_provider") or {}
        meta_table.add_row("Max completion", str(meta.get("max_completion") or top.get("max_completion_tokens") or "N/A"))
        meta_table.add_row("Moderation", str(meta.get("moderation") if meta.get("moderation") is not None else top.get("is_moderated", "N/A")))
        arch = meta.get("architecture")
        if arch is not None and str(arch).strip() not in ("", "None", "{}"):
            arch_text = _format_architecture(arch)
            meta_table.add_row("Architecture", arch_text)
        ek = meta.get("extra_keys") or []
        if ek:
            meta_table.add_row("Capabilities", _format_extra_keys(ek))
        console.print(Panel(meta_table, title=f"[{PASTEL_LAVENDER}]🌐 OpenRouter Metadata[/{PASTEL_LAVENDER}]", border_style=PASTEL_LAVENDER, box=ROUNDED))
        if dfull:
            console.print(
                Panel(
                    Markdown(dfull),
                    title=f"[bold {PASTEL_CYAN}]Mô tả đầy đủ (OpenRouter)[/bold {PASTEL_CYAN}]",
                    border_style=PASTEL_BLUE,
                    box=ROUNDED,
                    padding=(1, 2),
                )
            )
        bench = meta.get("benchmark_scores") or {}
        if bench:
            bt = Table(box=ROUNDED, title="Benchmark / metrics", border_style=PASTEL_LAVENDER)
            bt.add_column("Metric", style=PASTEL_CYAN, overflow="fold")
            bt.add_column("Val", justify="right", width=10)
            bt.add_column("Bar", width=34)
            for k, v in sorted(bench.items(), key=lambda x: str(x[0]))[:48]:
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                bt.add_row(str(k)[:44], f"{fv:.4f}", score_bar(fv))
            console.print(Panel(bt, border_style=PASTEL_LAVENDER, box=ROUNDED))
        else:
            console.print(
                "[dim]OpenRouter không cung cấp benchmark số cho model này.[/dim]"
            )
        console.print()

        console.print(
            f"[{PASTEL_LAVENDER}]Commands:[/{PASTEL_LAVENDER}] "
            f"[bold]change to <model_id>[/bold] | [bold]free models[/bold] | "
            f"[bold]change prompt[/bold] | [bold]change sampling[/bold] | "
            f"[bold]change reset[/bold] | [bold]back[/bold]"
        )
        try:
            cmd = Prompt.ask(f"[bold {PASTEL_CYAN}]>{role_key}[/bold {PASTEL_CYAN}]", default="back").strip()
        except (KeyboardInterrupt, EOFError):
            return

        cl = cmd.lower()
        if cl in ("back", "b", ""):
            return
        if cl == "exit":
            raise NavToMain

        if cl in ("free models", "free", "find free"):
            from utils.free_model_finder import show_free_model_picker
            show_free_model_picker(role_key=role_key.upper())
            wait_enter("Nhấn Enter để reload...")
            continue

        if cl.startswith("change to "):
            new_model = cmd[len("change to "):].strip()
            if not new_model:
                console.print("[yellow]⚠ Vui lòng nhập model id (vd: openai/gpt-4o).[/yellow]")
                wait_enter("Nhấn Enter để tiếp tục...")
                continue
            set_model_override(role_key.upper(), new_model)
            console.print(f"[green]✓ Đã đổi model của {role_key} → {new_model}[/green]")
            wait_enter("Nhấn Enter để reload...")
            continue

        if cl in ("change prompt", "prompt"):
            console.print()
            console.print(f"[{PASTEL_CYAN}]Nhập prompt mới cho {role_key}[/{PASTEL_CYAN}]")
            console.print("[dim](Prompt gốc không được hiển thị. Để trống = hủy)[/dim]")
            try:
                new_prompt = Prompt.ask("Prompt").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not new_prompt:
                console.print("[dim]Đã hủy — prompt không thay đổi.[/dim]")
                wait_enter("Nhấn Enter để tiếp tục...")
                continue
            set_prompt_override(role_key.upper(), new_prompt)
            console.print(f"[green]✓ Đã lưu prompt override cho {role_key}.[/green]")
            wait_enter("Nhấn Enter để reload...")
            continue

        if cl in ("change reset", "reset"):
            reset_all_role_overrides(role_key.upper())
            reset_sampling_override(role_key.upper())
            console.print(f"[green]✓ Đã reset model, prompt và sampling về mặc định cho {role_key}.[/green]")
            wait_enter("Nhấn Enter để reload...")
            continue

        if cl in ("change sampling", "sampling"):
            try:
                t = Prompt.ask("temperature (Enter bỏ qua)", default="").strip()
                p = Prompt.ask("top_p (Enter bỏ qua)", default="").strip()
                m = Prompt.ask("max_tokens (Enter bỏ qua)", default="").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            kwargs: dict = {}
            if t:
                try:
                    kwargs["temperature"] = float(t)
                except ValueError:
                    console.print("[yellow]temperature không hợp lệ[/yellow]")
            if p:
                try:
                    kwargs["top_p"] = float(p)
                except ValueError:
                    console.print("[yellow]top_p không hợp lệ[/yellow]")
            if m:
                try:
                    kwargs["max_tokens"] = int(m)
                except ValueError:
                    console.print("[yellow]max_tokens không hợp lệ[/yellow]")
            if kwargs:
                update_sampling_override(role_key.upper(), **kwargs)
                console.print(f"[green]✓ Đã lưu sampling override: {kwargs}[/green]")
            else:
                console.print("[dim]Không thay đổi sampling.[/dim]")
            wait_enter("Nhấn Enter để reload...")
            continue

        console.print(f"[yellow]Lệnh không nhận ra: {cmd}[/yellow]")
        wait_enter("Nhấn Enter để tiếp tục...")


__all__ = ["show_role_detail"]
