from __future__ import annotations

import json

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table

from core.cli.python_cli.shell.prompt import wait_enter
from core.cli.python_cli.features.change.helpers import indexed_workers, prompt_panel_content, score_bar
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.shell.state import (
    get_sampling_overrides,
    get_model_overrides,
    get_prompt_overrides,
    reset_all_role_overrides,
    reset_sampling_override,
    set_model_override,
    set_prompt_override,
    update_sampling_override,
)
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, clear_screen, console
from core.cli.python_cli.i18n import t as _t
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
            console.print(f"[red]{_t('info.role_not_found').format(role_key=role_key)}[/red]")
            return
        model_overrides = get_model_overrides()
        prompt_overrides = get_prompt_overrides()
        is_overridden = role_key.upper() in model_overrides
        has_prompt_override = role_key.upper() in prompt_overrides
        prompt_info = prompt_overrides.get(role_key.upper(), {})

        info = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
        info.add_column("K", style=Style(color=PASTEL_CYAN), width=18)
        info.add_column("V", style="white", width=50)
        info.add_row(_t("info.role_key"), f"[bold]{role_key}[/bold]")
        info.add_row(_t("info.role_name"), w["role"])
        raw_reason = w.get("reason", "")
        info.add_row(_t("info.reason"), f"[dim]{raw_reason}[/dim]" if raw_reason else "[dim]—[/dim]")
        info.add_row(_t("info.tier"), w.get("tier", "—"))
        info.add_row(_t("info.priority"), str(w.get("priority", "—")))
        
        active_label = f"[green]{_t('ui.yes')}[/green]" if w.get("active", True) else f"[red]{_t('ui.no')}[/red]"
        info.add_row(_t("info.active"), active_label)
        
        info.add_row(_t("info.model_eff"), f"[bold]{w['model']}[/bold]")
        if is_overridden:
            info.add_row(_t("info.default_model"), f"[dim]{w.get('default_model', '—')}[/dim]")
            info.add_row(_t("info.model_override"), f"[yellow]{_t('ui.active')}[/yellow]")
        pricing = w.get("pricing", {})
        info.add_row(_t("info.price_in"), f"${pricing.get('input', 0.0):.4f}" if pricing else "N/A")
        info.add_row(_t("info.price_out"), f"${pricing.get('output', 0.0):.4f}" if pricing else "N/A")
        
        samp = get_sampling_overrides().get(role_key.upper(), {}) or {}
        temp_val = samp.get("temperature", w.get("temperature", "—"))
        topp_val = samp.get("top_p", w.get("top_p", "—"))
        maxt_val = samp.get("max_tokens", w.get("max_tokens", "—"))
        effo_val = samp.get("reasoning_effort", w.get("reasoning_effort", "—"))
        
        temp_tag = " [yellow](ovr)[/yellow]" if "temperature" in samp else ""
        topp_tag = " [yellow](ovr)[/yellow]" if "top_p" in samp else ""
        maxt_tag = " [yellow](ovr)[/yellow]" if "max_tokens" in samp else ""
        effo_tag = " [yellow](ovr)[/yellow]" if "reasoning_effort" in samp else ""
        
        info.add_row(_t("info.temp"), f"{temp_val}{temp_tag}")
        info.add_row(_t("info.top_p"), f"{topp_val}{topp_tag}")
        info.add_row(_t("info.max_tokens"), f"{maxt_val}{maxt_tag}")
        info.add_row(_t("info.effort"), f"{effo_val}{effo_tag}")
        
        if samp:
            info.add_row(_t("info.sampling_ovr"), f"[yellow]{_t('ui.active')}[/yellow]")

        console.print(Panel(info, title=f"[bold {PASTEL_CYAN}]{role_key}[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))

        prompt_title = (
            _t("info.prompt_custom")
            if has_prompt_override and (prompt_info.get("prompt") or "").strip()
            else _t("info.prompt_title")
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

        console.print(f"[dim]{_t('ui.loading')} OpenRouter Metadata...[/dim]", end="\r")
        meta = fetch_model_detail(config.api_key, w["model"]) or {}
        dfull = str(meta.get("description") or "").strip()
        meta_table = Table(box=ROUNDED, show_header=False, border_style=PASTEL_LAVENDER, padding=(0, 2))
        meta_table.add_column("K", style=Style(color=PASTEL_LAVENDER), width=20)
        meta_table.add_column("V", style="white", overflow="fold")
        meta_table.add_row(_t("info.meta_name"), meta.get("name") or "N/A")
        meta_table.add_row(_t("info.meta_desc"), f"[dim]({_t('dash.history_desc').splitlines()[1].split(' · ')[1]})[/dim]" if dfull else "N/A")
        meta_table.add_row(_t("info.meta_ctx"), str(meta.get("context_length") or "N/A"))
        top = meta.get("top_provider") or {}
        meta_table.add_row(_t("info.meta_max_comp"), str(meta.get("max_completion") or top.get("max_completion_tokens") or "N/A"))
        meta_table.add_row(_t("info.meta_mod"), str(meta.get("moderation") if meta.get("moderation") is not None else top.get("is_moderated", "N/A")))
        arch = meta.get("architecture")
        if arch is not None and str(arch).strip() not in ("", "None", "{}"):
            arch_text = _format_architecture(arch)
            meta_table.add_row(_t("info.meta_arch"), arch_text)
        ek = meta.get("extra_keys") or []
        if ek:
            meta_table.add_row(_t("info.meta_cap"), _format_extra_keys(ek))
        console.print(Panel(meta_table, title=f"[{PASTEL_LAVENDER}]{_t('info.meta_title')}[/{PASTEL_LAVENDER}]", border_style=PASTEL_LAVENDER, box=ROUNDED))
        if dfull:
            console.print(
                Panel(
                    Markdown(dfull),
                    title=f"[bold {PASTEL_CYAN}]{_t('info.meta_desc')}[/bold {PASTEL_CYAN}]",
                    border_style=PASTEL_BLUE,
                    box=ROUNDED,
                    padding=(1, 2),
                )
            )
        bench = meta.get("benchmark_scores") or {}
        if bench:
            bt = Table(box=ROUNDED, title=_t("info.meta_bench_title"), border_style=PASTEL_LAVENDER)
            bt.add_column(_t("info.meta_bench_metric"), style=PASTEL_CYAN, overflow="fold")
            bt.add_column(_t("info.meta_bench_val"), justify="right", width=10)
            bt.add_column(_t("info.meta_bench_bar"), width=34)
            for k, v in sorted(bench.items(), key=lambda x: str(x[0]))[:48]:
                try:
                    fv = float(v)
                except (TypeError, ValueError):
                    continue
                bt.add_row(str(k)[:44], f"{fv:.4f}", score_bar(fv))
            console.print(Panel(bt, border_style=PASTEL_LAVENDER, box=ROUNDED))
        else:
            console.print(
                f"[dim]{_t('info.meta_none')}[/dim]"
            )
        console.print()

        console.print(
            f"[{PASTEL_LAVENDER}]{_t('info.cmd_label')}[/{PASTEL_LAVENDER}] "
            f"[bold]/model[/bold] | [bold]/free[/bold] | "
            f"[bold]/prompt[/bold] | [bold]/sampling[/bold] | "
            f"[bold]/reset[/bold] | [bold]/back[/bold]"
        )
        try:
            choice = ask_choice(
                f"[bold {PASTEL_CYAN}]{role_key}[/bold {PASTEL_CYAN}]",
                ["/back", "/exit", "/model", "/free", "/prompt", "/sampling", "/reset"],
                default="/back",
                context="agent_detail"
            )
        except (KeyboardInterrupt, EOFError):
            return

        if choice in (GLOBAL_EXIT, "/exit"):
            raise NavToMain
        if choice in (GLOBAL_BACK, "/back"):
            return

        if choice == "/free":
            from utils.free_model_finder import show_free_model_picker
            show_free_model_picker(role_key=role_key.upper())
            wait_enter(_t("ui.wait_enter"))
            continue

        if choice == "/model":
            console.print()
            from core.cli.python_cli.ui.palette_app import ask_with_palette
            new_model = ask_with_palette(f"{_t('info.model_col')} ", context="agent_detail").strip()
            if not new_model:
                console.print(f"[dim]{_t('ui.cancelled')}[/dim]")
                wait_enter(_t("ui.wait_enter"))
                continue
            set_model_override(role_key.upper(), new_model)
            console.print(f"[green]{role_key} → {new_model}[/green]")
            wait_enter(_t("ui.wait_enter"))
            continue

        if choice == "/prompt":
            console.print()
            console.print(f"[{PASTEL_CYAN}]Prompt: {role_key}[/{PASTEL_CYAN}]")
            console.print(f"[dim]({_t('context.subheader')} - {_t('ui.empty')} = cancel)[/dim]")
            try:
                from core.cli.python_cli.ui.palette_app import ask_with_palette
                new_prompt = ask_with_palette(f"{_t('info.prompt_title')} ", context="agent_detail").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            if not new_prompt:
                console.print(f"[dim]{_t('ui.cancelled')}[/dim]")
                wait_enter(_t("ui.wait_enter"))
                continue
            set_prompt_override(role_key.upper(), new_prompt)
            console.print(f"[green]{_t('ui.saved')}[/green]")
            wait_enter(_t("ui.wait_enter"))
            continue

        if choice == "/reset":
            reset_all_role_overrides(role_key.upper())
            reset_sampling_override(role_key.upper())
            console.print(f"[green]{_t('info.reset_ok').format(role=role_key)}[/green]")
            wait_enter(_t("ui.wait_enter"))
            continue

        if choice == "/sampling":
            try:
                from core.cli.python_cli.ui.palette_app import ask_with_palette
                t_val = ask_with_palette(f"{_t('info.sampling_hint').format(k='temperature')} ", context="agent_detail", default="").strip()
                p_val = ask_with_palette(f"{_t('info.sampling_hint').format(k='top_p')} ", context="agent_detail", default="").strip()
                m_val = ask_with_palette(f"{_t('info.sampling_hint').format(k='max_tokens')} ", context="agent_detail", default="").strip()
                e_val = ask_with_palette(f"{_t('info.effort_hint')} ", context="agent_detail", default="").strip()
            except (KeyboardInterrupt, EOFError):
                continue
            kwargs: dict = {}
            if t_val:
                try:
                    kwargs["temperature"] = float(t_val)
                except ValueError:
                    console.print(f"[yellow]{_t('nav.invalid_choice')} (temperature)[/yellow]")
            if p_val:
                try:
                    kwargs["top_p"] = float(p_val)
                except ValueError:
                    console.print(f"[yellow]{_t('nav.invalid_choice')} (top_p)[/yellow]")
            if m_val:
                try:
                    kwargs["max_tokens"] = int(m_val)
                except ValueError:
                    console.print(f"[yellow]{_t('nav.invalid_choice')} (max_tokens)[/yellow]")
            if e_val:
                ev = e_val.lower()
                if ev in ("low", "medium", "high"):
                    kwargs["reasoning_effort"] = ev
                else:
                    console.print(f"[yellow]{_t('nav.invalid_choice')} (effort: low/medium/high)[/yellow]")
            
            if kwargs:
                update_sampling_override(role_key.upper(), **kwargs)
                console.print(f"[green]✓ {_t('ui.saved')}: {kwargs}[/green]")
            else:
                console.print(f"[dim]{_t('ui.no_changes')}[/dim]")
            wait_enter(_t("ui.wait_enter"))
            continue

        console.print(f"[yellow]{_t('cmd.invalid_cmd').format(cmd=cmd)}[/yellow]")
        wait_enter(_t("ui.wait_enter"))


__all__ = ["show_role_detail"]
