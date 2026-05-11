"""Explainer state renderer -- using -> thinking -> writing (@codebase) or reading -> thinking -> writing (@file)."""
from __future__ import annotations

from core.cli.python_cli.i18n import t

_ORDER_CODEBASE = ("using", "thinking", "writing")
_ORDER_FILE     = ("reading", "thinking", "writing")


def _label(substate: str) -> str:
    return {
        "reading":  t("unit.reading"),
        "thinking": t("unit.thinking"),
        "writing":  t("unit.writing"),
        "using":    t("unit.using"),
    }.get(substate, substate)


def render_explainer_tree(sc: str, role: str, st: dict, elapsed: int = 0) -> str:
    """Render the Explainer live tree.

    st keys: substate, detail, mode ("codebase"|"file"), buf, is_done
    """
    is_done  = bool(st.get("is_done"))
    substate = str(st.get("substate") or "using")
    detail   = str(st.get("detail") or "")
    mode     = str(st.get("mode") or "codebase")
    buf      = str(st.get("buf") or "")

    order = _ORDER_CODEBASE if mode == "codebase" else _ORDER_FILE
    sc_part = "[bold green]*[/bold green]" if is_done else f"[#888888]{sc}[/#888888]"
    parts = [f"{sc_part} [bold]{role}[/bold]"]

    if is_done:
        for i, s in enumerate(order):
            connector = "+-" if i == len(order) - 1 else "+-"
            parts.append(f"[dim]{connector}[/dim] {_label(s)} [green]OK[/green]")
        return "\n".join(parts)

    try:
        cur_idx = order.index(substate)
    except ValueError:
        cur_idx = 0

    for s in order[:cur_idx]:
        parts.append(f"[dim]+-[/dim] {_label(s)} [green]OK[/green]")

    spin = f" [bold blue]{sc}[/bold blue]"
    elapsed_str = f"  [dim]({elapsed}s)[/dim]" if elapsed else ""
    parts.append(f"[dim]+-[/dim] {_label(substate)}{spin}{elapsed_str}")

    if substate == "thinking" and buf:
        lines = [ln for ln in buf.split("\n") if ln.strip()][-6:]
        for j, ln in enumerate(lines):
            pfx = "[dim]  +-[/dim]" if j == 0 else "[dim]    [/dim]"
            safe = ln.replace("[", r"\[")
            parts.append(f"{pfx} [dim]{safe[:94]}[/dim]")
    elif detail:
        safe = detail.replace("[", r"\[")
        parts.append(f"  [dim]+-[/dim] [dim]{safe[:90]}[/dim]")

    return "\n".join(parts)


def render_explainer_done(role: str, output_file: str = "") -> str:
    head = f"[bold green]*[/bold green] [bold]{role}[/bold]"
    if output_file:
        safe = output_file.replace("[", r"\[")
        head += f"  [dim]-> {safe}[/dim]"
    branches = [
        f"[dim]+-[/dim] {_label('using')} [green]OK[/green]",
        f"[dim]+-[/dim] {_label('thinking')} [green]OK[/green]",
        f"[dim]+-[/dim] {_label('writing')} [green]OK[/green]",
    ]
    return "\n".join([head, *branches])
