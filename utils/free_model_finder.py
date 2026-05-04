"""Free model finder — fetches zero-cost models from OpenRouter and presents them in the CLI.

Usage (standalone):
    from utils.free_model_finder import find_free_models, show_free_model_picker

    models = find_free_models()          # list of {id, name, context_length, ...}
    chosen = show_free_model_picker()    # interactive picker; returns model id or None
"""

from __future__ import annotations

import logging
import urllib.request
import json
from typing import Optional

logger = logging.getLogger(__name__)

_OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
_TIMEOUT = 8


def find_free_models() -> list[dict]:
    """Fetch models from OpenRouter; return those with pricing.prompt == '0'."""
    try:
        req = urllib.request.Request(
            _OPENROUTER_MODELS_URL,
            headers={"User-Agent": "aiteam/6.2.0"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:  # nosec B310
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        logger.warning("free_model_finder: fetch failed (%s: %s)", type(e).__name__, e)
        return []

    models = payload.get("data") or []
    free: list[dict] = []
    for m in models:
        pricing = m.get("pricing") or {}
        prompt_cost = pricing.get("prompt", "1")
        try:
            if float(prompt_cost) == 0.0:
                free.append({
                    "id": m.get("id", ""),
                    "name": m.get("name", m.get("id", "")),
                    "context_length": m.get("context_length", 0),
                    "description": (m.get("description") or "")[:120],
                })
        except (TypeError, ValueError):
            pass

    return sorted(free, key=lambda x: x["name"].lower())


def show_free_model_picker(role_key: str | None = None) -> Optional[str]:
    """Show interactive TUI picker for free models on OpenRouter.

    If *role_key* is given, offers to set it as the model override for that
    role (with automatic revert option). Returns chosen model id, or None.
    """
    from rich.box import ROUNDED, SIMPLE
    from rich.panel import Panel
    from rich.style import Style
    from rich.table import Table
    from rich.prompt import Prompt
    from core.cli.python_cli.ui.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, console
    from core.cli.python_cli.i18n import t

    console.print(f"\n[{PASTEL_CYAN}]{t('ui.fetching_free')}[/{PASTEL_CYAN}]")
    with console.status(f"[{PASTEL_BLUE}]{t('ui.loading')}[/{PASTEL_BLUE}]"):
        models = find_free_models()

    if not models:
        console.print(f"[yellow]{t('dash.no_history')}[/yellow]")
        return None

    tbl = Table(box=SIMPLE, show_header=True,
                header_style=Style(color=PASTEL_CYAN, bold=True),
                border_style=PASTEL_BLUE, padding=(0, 1))
    tbl.add_column("#", style="dim", width=4)
    tbl.add_column(t("info.model_id"), style=Style(color=PASTEL_CYAN), width=48)
    tbl.add_column(t("info.role_name"), style=Style(color=SOFT_WHITE), width=30)
    tbl.add_column(t("ui.col_ctx"), justify="right", width=10)
    for i, m in enumerate(models, 1):
        ctx = f"{m['context_length']:,}" if m["context_length"] else "—"
        tbl.add_row(str(i), m["id"], m["name"], ctx)

    console.print(Panel(tbl, title=f"[bold]{t('info.free_title')}[/bold]",
                        border_style=PASTEL_BLUE, box=ROUNDED))
    console.print(f"[dim]{t('info.free_select_hint')}[/dim]")

    try:
        raw = Prompt.ask(f"[{PASTEL_CYAN}]{t('ui.select_num')}[/{PASTEL_CYAN}]", default="").strip()
    except (KeyboardInterrupt, EOFError):
        return None

    if not raw:
        return None

    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(models)):
            console.print(f"[red]{t('nav.invalid_choice')}[/red]")
            return None
    except ValueError:
        console.print(f"[red]{t('ui.invalid_retry')}[/red]")
        return None

    chosen_id = models[idx]["id"]
    console.print(f"\n[green]{t('info.selected')}[/green] {chosen_id}")
    console.print(f"[dim]{t('info.copy_hint')}[/dim]")

    if role_key:
        _apply_free_model_override(role_key, chosen_id, console, PASTEL_CYAN)

    return chosen_id


def _apply_free_model_override(role_key: str, model_id: str, console, PASTEL_CYAN: str) -> None:
    """Apply model override for role_key immediately (no confirmation)."""
    from core.cli.python_cli.shell.state import set_model_override, get_model_overrides
    from core.config import config
    from core.cli.python_cli.i18n import t

    original = get_model_overrides().get(role_key) or (config.get_worker(role_key) or {}).get("model", "")
    set_model_override(role_key, model_id)
    console.print(f"[green]{t('info.ovr_set')}[/green] {role_key} → {model_id}")
    if original:
        console.print(f"[dim]{t('info.prev_model').format(m=original)}[/dim]")


__all__ = ["find_free_models", "show_free_model_picker"]
