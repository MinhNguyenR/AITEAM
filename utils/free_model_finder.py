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
    from core.cli.python_cli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, SOFT_WHITE, console

    console.print(f"\n[{PASTEL_CYAN}]Fetching free models from OpenRouter…[/{PASTEL_CYAN}]")
    with console.status(f"[{PASTEL_BLUE}]Loading…[/{PASTEL_BLUE}]"):
        models = find_free_models()

    if not models:
        console.print("[yellow]No free models found (network error or none available).[/yellow]")
        return None

    tbl = Table(box=SIMPLE, show_header=True,
                header_style=Style(color=PASTEL_CYAN, bold=True),
                border_style=PASTEL_BLUE, padding=(0, 1))
    tbl.add_column("#", style="dim", width=4)
    tbl.add_column("Model ID", style=Style(color=PASTEL_CYAN), width=48)
    tbl.add_column("Name", style=Style(color=SOFT_WHITE), width=30)
    tbl.add_column("Ctx", justify="right", width=10)
    for i, m in enumerate(models, 1):
        ctx = f"{m['context_length']:,}" if m["context_length"] else "—"
        tbl.add_row(str(i), m["id"], m["name"], ctx)

    console.print(Panel(tbl, title="[bold]Free Models (OpenRouter)[/bold]",
                        border_style=PASTEL_BLUE, box=ROUNDED))
    console.print("[dim]Enter a number to select, or press Enter to cancel.[/dim]")

    try:
        raw = Prompt.ask(f"[{PASTEL_CYAN}]Select #[/{PASTEL_CYAN}]", default="").strip()
    except (KeyboardInterrupt, EOFError):
        return None

    if not raw:
        return None

    try:
        idx = int(raw) - 1
        if not (0 <= idx < len(models)):
            console.print("[red]Invalid selection.[/red]")
            return None
    except ValueError:
        console.print("[red]Please enter a number.[/red]")
        return None

    chosen_id = models[idx]["id"]
    console.print(f"\n[green]Selected:[/green] {chosen_id}")
    console.print("[dim](Copy the ID above to paste into model override, or press Enter to apply now.)[/dim]")

    if role_key:
        _apply_free_model_override(role_key, chosen_id, console, PASTEL_CYAN)

    return chosen_id


def _apply_free_model_override(role_key: str, model_id: str, console, PASTEL_CYAN: str) -> None:
    """Apply model override for role_key immediately (no confirmation)."""
    from core.cli.python_cli.state import set_model_override, get_model_overrides
    from core.config import config

    original = get_model_overrides().get(role_key) or (config.get_worker(role_key) or {}).get("model", "")
    set_model_override(role_key, model_id)
    console.print(f"[green]✓ Override set:[/green] {role_key} → {model_id}")
    if original:
        console.print(f"[dim]Previous model: {original}  (type 'change reset' to revert)[/dim]")


__all__ = ["find_free_models", "show_free_model_picker"]
