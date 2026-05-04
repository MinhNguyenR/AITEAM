"""Pipeline-level state renderers — idle, transitional, finalizing, btw."""
from __future__ import annotations

from core.cli.python_cli.i18n import t


def render_idle() -> str:
    return ""


def render_transitional(sc: str) -> str:
    """Between ambassador done and leader_generate becoming active."""
    return f"[dim]{sc} {t('pipeline.reading')}[/dim]"


def render_finalizing(sc: str) -> str:
    return f"[dim]{sc}[/dim] [bold]Finalize[/bold]\n[dim]└── {t('pipeline.finalizing')}[/dim]"


def render_unknown(sc: str, step: str) -> str:
    return f"[dim]{sc} {step}[/dim]"


def render_btw_injecting(sc: str, role_name: str) -> str:
    return (
        f"[dim]{sc}[/dim] [bold]{role_name}[/bold]\n"
        f"[dim]└── {t('pipeline.btw_checking')}[/dim]"
    )
