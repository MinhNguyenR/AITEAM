"""Tool Curator state renderer — branching tree across 4 substates.

Substates:
    reading      → reads context.md
    thinking     → LLM analyzing dependencies (out tokens stream)
    looking_for  → scanning project files / pip list
    writing      → writing tools.md (out tokens stream)
"""
from __future__ import annotations

from core.cli.python_cli.i18n import t


_ORDER = ("reading", "thinking", "looking_for", "writing")


def _label(substate: str) -> str:
    return {
        "reading":     t("curator.reading"),
        "thinking":    t("curator.thinking"),
        "looking_for": t("curator.looking_for"),
        "writing":     t("curator.writing"),
    }.get(substate, substate)


def _meta(*vals: str) -> str:
    filt = [str(v) for v in vals if v]
    return f"  [dim]({'  '.join(filt)})[/dim]" if filt else ""


def render_curator_tree(sc: str, role: str, st: dict, elapsed: int = 0) -> str:
    """Render the Tool Curator live tree.

    st keys: substate, detail, pt, ct, is_done
    """
    is_done  = bool(st.get("is_done"))
    substate = str(st.get("substate") or "reading")
    detail   = str(st.get("detail") or "")
    pt       = int(st.get("pt") or 0)
    ct       = int(st.get("ct") or 0)

    sc_part = "[bold green]●[/bold green]" if is_done else f"[#888888]{sc}[/#888888]"
    parts = [f"{sc_part} [bold]{role}[/bold]"]

    if is_done:
        for s in _ORDER:
            parts.append(f"[dim]├─[/dim] {_label(s)} [green]✓[/green]")
        # Replace last connector with └─ for tidiness
        if len(parts) >= 2:
            parts[-1] = parts[-1].replace("├─", "└─", 1)
        return "\n".join(parts)

    try:
        cur_idx = _ORDER.index(substate)
    except ValueError:
        cur_idx = 0

    for i, s in enumerate(_ORDER[:cur_idx]):
        parts.append(f"[dim]├─[/dim] {_label(s)} [green]✓[/green]")

    # Active substate (last)
    spin = f" [bold blue]{sc}[/bold blue]"
    meta_bits: list[str] = []
    if elapsed:
        meta_bits.append(f"{elapsed}s")
    if substate in ("reading",) and pt:
        meta_bits.append(f"in:{pt:,}")
    if substate in ("thinking", "writing") and ct:
        meta_bits.append(f"out:{ct:,}")
    meta = _meta(*meta_bits)

    parts.append(f"[dim]└─[/dim] {_label(substate)}{spin}{meta}")
    if detail:
        safe = detail.replace("[", r"\[")
        parts.append(f"  [dim]└─[/dim] [dim]{safe[:94]}[/dim]")
    return "\n".join(parts)


def render_curator_done(role: str, tok: str = "") -> str:
    head = f"[bold green]●[/bold green] [bold]{role}[/bold]{tok}"
    branches = [
        f"[dim]├─[/dim] {_label('reading')} [green]✓[/green]",
        f"[dim]├─[/dim] {_label('thinking')} [green]✓[/green]",
        f"[dim]├─[/dim] {_label('looking_for')} [green]✓[/green]",
        f"[dim]└─[/dim] {_label('writing')} [green]✓[/green]",
    ]
    return "\n".join([head, *branches])
