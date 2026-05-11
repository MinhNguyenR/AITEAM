"""Human gate state renderers -- completely separate state from leader."""
from __future__ import annotations

from core.cli.python_cli.i18n import t


def render_waiting(sc: str) -> str:
    return (
        f"[#888888]{sc}[/#888888] [bold]Human Gate[/bold]\n"
        f"[dim]+-[/dim] {t('gate.waiting')}\n"
        f"    [dim]+-[/dim] [dim]{t('gate.hint')}[/dim]"
    )


def render_checking(sc: str) -> str:
    return (
        f"[#888888]{sc}[/#888888] [bold]Human Gate[/bold]\n"
        f"[dim]+-[/dim] {t('gate.waiting')}\n"
        f"[dim]+-[/dim] [yellow]{t('gate.checking')}[/yellow]\n"
        f"    [dim]+-[/dim] [dim][bold]/accept[/bold]  .  [bold]/delete[/bold]  .  {t('context.edit_hint')}[/dim]"
    )


def render_editing(sc: str) -> str:
    return (
        f"[#888888]{sc}[/#888888] [bold]Human Gate[/bold]\n"
        f"[dim]+-[/dim] {t('gate.waiting')}\n"
        f"[dim]+-[/dim] [yellow]{t('gate.editing')}[/yellow]"
    )


def render_accepted() -> str:
    return (
        f"[bold green]*[/bold green] [bold]Human Gate[/bold]\n"
        f"[dim]+-[/dim] [green]✓ {t('context.accepted_msg')}[/green]"
    )


def render_declined(sc: str) -> str:
    return (
        f"[bold red]*[/bold red] [bold]Human Gate[/bold]\n"
        f"[dim]+-[/dim] [red]✗ {t('gate.declined')}[/red]\n"
        f"[dim]+-[/dim] [#888888]{sc}[/#888888] {t('gate.regen_prompt')}"
    )
