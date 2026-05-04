from __future__ import annotations

from typing import Callable

from rich.box import ROUNDED
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt

from core.cli.python_cli.shell.prompt import ask_choice, wait_enter
from core.cli.python_cli.shell.safe_editor import run_editor_on_file
from core.cli.python_cli.features.context.common import (
    delete_state_json_on_accept,
    find_context_md,
    full_context_cleanup,
    graphrag_drop,
)
from core.cli.python_cli.shell.nav import NavToMain
from core.cli.python_cli.shell.state import load_context_state, log_system_action, update_context_state
from core.cli.python_cli.workflow.runtime import session as ws
from core.cli.python_cli.workflow.runtime.graph.runner import resume_workflow
from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, clear_screen, console, print_header
from core.cli.python_cli.i18n import t
from core.cli.python_cli.shell.choice_lists import context_viewer_choices
from core.domain.delta_brief import is_no_context


def show_context(project_root: str, start_runner: Callable[[str], None]) -> None:
    clear_screen()
    print_header(t("context.viewer_header"))
    state = load_context_state()
    if state.get("status") in ("completed", "deleted"):
        console.print(f"[dim]{t('context.no_active')}[/dim]")
        wait_enter()
        clear_screen()
        return
    ctx = find_context_md(project_root)
    if not ctx:
        console.print(
            Panel(
                f"[yellow]{t('context.not_found')}[/yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()
        wait_enter()
        clear_screen()
        return
    if is_no_context(ctx):
        console.print(
            Panel(
                f"[bold red]{t('context.sentinel')}[/bold red]",
                border_style="red",
                padding=(1, 2),
            )
        )
        console.print()
        wait_enter()
        clear_screen()
        return
    if ws.is_paused_for_review():
        console.print(
            Panel(
                f"[bold yellow]{t('context.paused_hint')}[/bold yellow]",
                border_style="yellow",
                padding=(1, 2),
            )
        )
        console.print()
    content = ctx.read_text(encoding="utf-8")
    lines = content.splitlines()
    console.print(f"[{PASTEL_CYAN}]{ctx}[/{PASTEL_CYAN}]  [dim]{len(lines)} {t('unit.lines')}[/dim]")
    console.print()
    display = "\n".join(lines[:150])
    if len(lines) > 150:
        display += f"\n\n[dim]{t('context.lines_hidden').format(n=len(lines)-150)}[/dim]"
    console.print(Panel(Markdown(display), title=f"[bold {PASTEL_CYAN}]context.md[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, padding=(1, 2), box=ROUNDED))
    console.print()
    while True:
        opts_labels = [
            f"[bold]/back[/bold]",
            f"[bold]/edit[/bold]",
            f"[bold red]/delete[/bold red]",
            f"[bold green]/run[/bold green]",
            f"[bold]/regenerate[/bold]",
            f"[bold]/exit[/bold]"
        ]
        console.print(f"[{PASTEL_CYAN}]{t('ui.options')}[/{PASTEL_CYAN}] {' | '.join(opts_labels)}")
        choice = ask_choice(t("ui.choice"), ["/back", "/exit", "/run", "/edit", "/delete", "/regenerate"], default="/back", context="context_viewer")
        if choice in ("exit", "/exit"):
            clear_screen()
            raise NavToMain
        if choice in ("back", "/back"):
            if ws.is_paused_for_review():
                ws.set_should_finalize(False)
                ws.set_context_accept_status("deferred")
                ws.set_pipeline_paused_at_gate(True)
                ws.set_phase_paused_gate()
            clear_screen()
            return
        if choice == "/edit":
            console.print(f"[dim]{t('context.opening_editor').format(path=ctx)}[/dim]")
            run_editor_on_file(ctx)
            clear_screen()
            print_header(t("context.viewer_header"))
            content = ctx.read_text(encoding="utf-8")
            lines = content.splitlines()
            display = "\n".join(lines[:150])
            if len(lines) > 150:
                display += f"\n\n[dim]{t('context.lines_hidden').format(n=len(lines)-150)}[/dim]"
            console.print(Panel(Markdown(display), title=f"[bold {PASTEL_CYAN}]context.md[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, padding=(1, 2), box=ROUNDED))
            console.print()
            continue
        if choice == "/delete":
            try:
                full_context_cleanup(ctx, reason="deleted")
                console.print(f"[green]{t('context.deleted')}[/green]")
            except (OSError, ValueError, TypeError) as e:
                console.print(f"[red]{t('context.delete_error').format(e=e)}[/red]")
            wait_enter()
            clear_screen()
            return
        if choice == "/run":
            try:
                graphrag_drop(ctx)
                ctx.unlink(missing_ok=True)
            except OSError as e:
                console.print(f"[red]{t('context.delete_error').format(e=e)}[/red]")
            delete_state_json_on_accept(ctx)
            update_context_state("completed", ctx, reason="run_from_check")
            log_system_action("context.run", str(ctx))
            console.print(f"[green]{t('context.accepted')}[/green]")
            if ws.is_paused_for_review():
                ws.set_should_finalize(True)
                ws.set_context_accept_status("accepted")
                resume_workflow()
            wait_enter()
            clear_screen()
            return
        if choice == "/regenerate":
            try:
                graphrag_drop(ctx)
                ctx.unlink(missing_ok=True)
            except OSError as e:
                console.print(f"[red]{t('context.delete_error').format(e=e)}[/red]")
            update_context_state("deleted", ctx, reason="regenerate_from_check")
            log_system_action("context.delete", f"{ctx} reason=regenerate_from_check")
            if ws.is_paused_for_review():
                ws.set_paused_for_review(False)
            from core.cli.python_cli.ui.palette import ask_with_palette
            prompt = ask_with_palette(f"{t('context.new_task_hint')} ", context="context_viewer")
            pt = (prompt or "").strip()
            pl = pt.lower()
            if pl in ("/exit", "exit"):
                raise NavToMain
            if pl in ("/back", "back"):
                clear_screen()
                return
            if pt:
                start_runner(pt)
            clear_screen()
            return


__all__ = ["show_context"]
