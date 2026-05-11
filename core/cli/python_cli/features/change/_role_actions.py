"""Action handlers for the role detail screen.

Each function returns True if the caller should `return` (exit the loop),
False if the caller should `continue`. NavToMain propagates naturally.
"""
from __future__ import annotations

from rich.box import ROUNDED
from rich.panel import Panel

from core.cli.python_cli.shell.prompt import wait_enter
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.shell.state import (
    reset_all_role_overrides,
    reset_sampling_override,
    set_model_override,
    set_prompt_override,
    update_sampling_override,
)
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, console
from core.cli.python_cli.i18n import t as _t


def action_free(role_key: str) -> bool:
    from utils.free_model_finder import show_free_model_picker
    show_free_model_picker(role_key=role_key.upper())
    wait_enter(_t("ui.wait_enter"))
    return False


def action_model(role_key: str) -> bool:
    from rich.prompt import Prompt
    console.print()
    console.print(Panel(
        "[dim]Nhập ID model OpenRouter (vd: google/gemini-2.5-flash)[/dim]",
        title=f"[{PASTEL_CYAN}]🤖 Thay đổi Model: {role_key}[/{PASTEL_CYAN}]",
        border_style=PASTEL_BLUE, box=ROUNDED,
    ))
    try:
        new_model = Prompt.ask(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]").strip()
    except (KeyboardInterrupt, EOFError):
        return False

    if new_model.lower() == "exit":
        raise NavToMain
    if new_model.lower() == "back":
        return True

    if not new_model:
        console.print(f"[dim]{_t('ui.cancelled')}[/dim]")
        wait_enter(_t("ui.wait_enter"))
        return False

    with console.status(f"[{PASTEL_BLUE}]Đang kiểm tra tính hợp lệ của model...[/{PASTEL_BLUE}]"):
        valid = False
        try:
            import urllib.request, json as _json
            req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "aiteam/6.2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                payload = _json.loads(resp.read().decode("utf-8"))
                all_ids = {m.get("id") for m in payload.get("data", []) if m.get("id")}
                if new_model in all_ids:
                    valid = True
                elif f"openrouter/{new_model}" in all_ids:
                    new_model = f"openrouter/{new_model}"
                    valid = True
        except Exception:
            valid = True  # allow through if network unavailable

    if not valid:
        console.print(f"[red]✘ Model '{new_model}' không tồn tại trên OpenRouter![/red]")
        wait_enter(_t("ui.wait_enter"))
        return False

    set_model_override(role_key.upper(), new_model)
    console.print(f"[green]✔ {role_key} -> {new_model}[/green]")
    wait_enter(_t("ui.wait_enter"))
    return False


def action_prompt(role_key: str) -> bool:
    from rich.prompt import Prompt
    console.print()
    console.print(Panel(
        f"[dim]{_t('context.subheader')} - để trống để hủy[/dim]",
        title=f"[{PASTEL_CYAN}]📝 Thay đổi Prompt: {role_key}[/{PASTEL_CYAN}]",
        border_style=PASTEL_BLUE, box=ROUNDED,
    ))
    try:
        new_prompt = Prompt.ask(f"[{PASTEL_CYAN}]>[/{PASTEL_CYAN}]").strip()
    except (KeyboardInterrupt, EOFError):
        return False

    if new_prompt.lower() == "exit":
        raise NavToMain
    if new_prompt.lower() == "back":
        return True

    if not new_prompt:
        console.print(f"[dim]{_t('ui.cancelled')}[/dim]")
        wait_enter(_t("ui.wait_enter"))
        return False

    if len(new_prompt.split()) < 6:
        console.print(f"[yellow]✘ Prompt quá ngắn (cần tối thiểu 6 từ/token)[/yellow]")
        wait_enter(_t("ui.wait_enter"))
        return False

    set_prompt_override(role_key.upper(), new_prompt)
    console.print(f"[green]✔ {_t('ui.saved')}[/green]")
    wait_enter(_t("ui.wait_enter"))
    return False


def action_sampling(role_key: str) -> bool:
    from rich.prompt import Prompt
    console.print()
    console.print(Panel(
        "[dim]Nhập giá trị mới hoặc để trống để giữ nguyên.[/dim]",
        title=f"[{PASTEL_CYAN}]⚙️ Cấu hình Sampling: {role_key}[/{PASTEL_CYAN}]",
        border_style=PASTEL_BLUE, box=ROUNDED,
    ))
    try:
        kwargs: dict = {}
        while True:
            t_val = Prompt.ask(f"[{PASTEL_CYAN}]Temperature[/{PASTEL_CYAN}] [dim](0.0-2.0)[/dim]").strip()
            if t_val.lower() == "exit": raise NavToMain
            if t_val.lower() == "back": return True
            if not t_val: break
            try:
                tv = float(t_val)
                if 0.0 <= tv <= 2.0:
                    kwargs["temperature"] = tv
                    break
                console.print(f"[yellow]✘ Giá trị ngoài khoảng (0.0 - 2.0)[/yellow]")
            except ValueError:
                console.print(f"[yellow]✘ Vui lòng nhập số hợp lệ[/yellow]")

        while True:
            p_val = Prompt.ask(f"[{PASTEL_CYAN}]Top P[/{PASTEL_CYAN}] [dim](0.0-1.0)[/dim]").strip()
            if p_val.lower() == "exit": raise NavToMain
            if p_val.lower() == "back": return True
            if not p_val: break
            try:
                pv = float(p_val)
                if 0.0 <= pv <= 1.0:
                    kwargs["top_p"] = pv
                    break
                console.print(f"[yellow]✘ Giá trị ngoài khoảng (0.0 - 1.0)[/yellow]")
            except ValueError:
                console.print(f"[yellow]✘ Vui lòng nhập số hợp lệ[/yellow]")

        while True:
            m_val = Prompt.ask(f"[{PASTEL_CYAN}]Max Tokens[/{PASTEL_CYAN}] [dim](>= 1000)[/dim]").strip()
            if m_val.lower() == "exit": raise NavToMain
            if m_val.lower() == "back": return True
            if not m_val: break
            try:
                mv = int(m_val)
                if mv >= 1000:
                    kwargs["max_tokens"] = mv
                    break
                console.print(f"[yellow]✘ Giá trị quá nhỏ (cần >= 1000)[/yellow]")
            except ValueError:
                console.print(f"[yellow]✘ Vui lòng nhập số nguyên hợp lệ[/yellow]")

        while True:
            e_val = Prompt.ask(f"[{PASTEL_CYAN}]Reasoning Effort[/{PASTEL_CYAN}] [dim](low/medium/high)[/dim]").strip()
            if e_val.lower() == "exit": raise NavToMain
            if e_val.lower() == "back": return True
            if not e_val: break
            ev = e_val.lower()
            if ev in ("low", "medium", "high"):
                kwargs["reasoning_effort"] = ev
                break
            console.print(f"[yellow]✘ Vui lòng nhập low, medium, hoặc high[/yellow]")
    except (KeyboardInterrupt, EOFError):
        return False

    if kwargs:
        update_sampling_override(role_key.upper(), **kwargs)
        console.print(f"[green]✔ {_t('ui.saved')}[/green]")
    else:
        console.print(f"[dim]{_t('ui.cancelled')}[/dim]")
    wait_enter(_t("ui.wait_enter"))
    return False


def action_reset(role_key: str) -> bool:
    reset_all_role_overrides(role_key.upper())
    reset_sampling_override(role_key.upper())
    console.print(f"[green]{_t('info.reset_ok').format(role=role_key)}[/green]")
    wait_enter(_t("ui.wait_enter"))
    return False


__all__ = ["action_free", "action_model", "action_prompt", "action_sampling", "action_reset"]
