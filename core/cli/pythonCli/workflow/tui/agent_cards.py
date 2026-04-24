"""Agent card data model and renderers — shared by chain and list workflow views.

Designed to scale: add new roles/nodes by adding entries to STATUS_ICON /
STATUS_BADGE and updating monitor_helpers._steps_for_tier + _display_name.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import config
from .monitor_helpers import _display_name, _registry_key_for_step

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

STATUS_ICON: dict[str, tuple[str, str]] = {
    "running": ("↻", "yellow"),
    "complete": ("✓", "green"),
    "error":    ("✗", "red"),
    "wait":     ("◉", "yellow"),
    "pending":  ("○", "grey46"),
}

STATUS_BADGE: dict[str, str] = {
    "running": "[bold yellow]RUNNING[/bold yellow]",
    "complete": "[bold green]DONE   [/bold green]",
    "error":    "[bold red]ERROR  [/bold red]",
    "wait":     "[yellow]WAITING[/yellow]",
    "pending":  "[dim]PENDING[/dim]",
}


@dataclass
class AgentCard:
    node_id: str
    display_name: str
    model_name: str
    status: str       # running | complete | error | wait | pending
    detail: str
    stream_tail: str  # recent chars from LLM stream buffer


def short_model(full_model: str) -> str:
    if "/" in full_model:
        return full_model.rsplit("/", 1)[-1]
    return full_model


def model_for_node(node_id: str, tier: str | None, selected_leader: str) -> str:
    key = _registry_key_for_step(node_id, tier)
    if not key:
        return ""
    cfg = config.get_worker(key) or {}
    return short_model(str(cfg.get("model", "") or ""))


def get_agent_cards(snap: dict[str, Any], steps: list[str]) -> list[AgentCard]:
    tier = snap.get("brief_tier")
    selected_leader = str(snap.get("brief_selected_leader") or "")
    nodes_state: list[dict] = snap.get("workflow_list_nodes_state") or []
    node_map = {str(n.get("node", "")): n for n in nodes_state}
    active = str(snap.get("active_step") or "idle")
    stream_buf = str(snap.get("leader_stream_buffer") or "")
    paused = bool(snap.get("paused_at_gate"))

    cards: list[AgentCard] = []
    for sid in steps:
        ns = node_map.get(sid, {})
        raw = str(ns.get("status") or "pending").lower()

        if raw == "complete":
            status = "complete"
        elif raw == "error":
            status = "error"
        elif sid == "human_context_gate" and paused:
            status = "wait"
        elif raw == "running" or sid == active:
            status = "running"
        else:
            status = "pending"

        detail = str(ns.get("detail") or "")
        stream_tail = ""
        if status == "running" and stream_buf:
            stream_tail = stream_buf[-200:].lstrip()

        cards.append(AgentCard(
            node_id=sid,
            display_name=_display_name(sid),
            model_name=model_for_node(sid, tier, selected_leader),
            status=status,
            detail=detail,
            stream_tail=stream_tail,
        ))
    return cards


def render_cards_markup(cards: list[AgentCard], spin_idx: int) -> str:
    """Rich markup for Textual Static or Rich console rendering."""
    if not cards:
        return "[dim]—[/dim]"
    sc = SPINNER[spin_idx % len(SPINNER)]
    lines: list[str] = []
    for card in cards:
        icon, col = STATUS_ICON.get(card.status, ("○", "grey46"))
        glyph = sc if card.status == "running" else icon
        model_s = f"  [dim cyan]{card.model_name}[/dim cyan]" if card.model_name else ""
        lines.append(f"[{col}]{glyph}[/{col}] [bold]{card.display_name}[/bold]{model_s}")
        if card.status == "running" and card.stream_tail:
            preview = card.stream_tail.replace("\n", " ").strip()
            if len(preview) > 90:
                preview = preview[:87] + "..."
            lines.append(f"  [dim italic]▸ {preview}[/dim italic]")
        elif card.detail and card.status != "pending":
            lines.append(f"  [dim]→ {card.detail[:80]}[/dim]")
    return "\n".join(lines)


__all__ = [
    "AgentCard",
    "SPINNER",
    "STATUS_ICON",
    "STATUS_BADGE",
    "get_agent_cards",
    "model_for_node",
    "render_cards_markup",
    "short_model",
]
