"""Tool Curator state renderer."""
from __future__ import annotations

from core.cli.python_cli.i18n import t

_ORDER = ("reading", "thinking", "looking_for", "writing")


def _label(substate: str) -> str:
    return {
        "reading": t("unit.reading"),
        "thinking": t("unit.thinking"),
        "looking_for": t("unit.using"),
        "writing": t("unit.writing"),
    }.get(substate, substate)


def _meta(*vals: str) -> str:
    filt = [str(v) for v in vals if v]
    return f"  [dim]({'  '.join(filt)})[/dim]" if filt else ""


def _safe(text: object, limit: int = 98) -> str:
    return str(text or "").replace("[", r"\[")[:limit]


def render_curator_tree(sc: str, role: str, st: dict, elapsed: int = 0) -> str:
    is_done = bool(st.get("is_done"))
    substate = str(st.get("substate") or "reading")
    detail = str(st.get("detail") or "")
    pt = int(st.get("pt") or 0)
    ct = int(st.get("ct") or 0)
    buf = str(st.get("buf") or "")

    sc_part = "[bold green]*[/bold green]" if is_done else f"[#888888]{sc}[/#888888]"
    parts = [f"{sc_part} [bold]{role}[/bold]"]

    if is_done:
        for i, s in enumerate(_ORDER):
            conn = "`-" if i == len(_ORDER) - 1 else "+-"
            parts.append(f"[dim]{conn}[/dim] {_label(s)} [green]OK[/green]")
        return "\n".join(parts)

    try:
        cur_idx = _ORDER.index(substate)
    except ValueError:
        cur_idx = 0

    for i, s in enumerate(_ORDER[:cur_idx]):
        conn = "+-" if i < cur_idx else "`-"
        parts.append(f"[dim]{conn}[/dim] {_label(s)} [green]OK[/green]")

    meta_bits: list[str] = []
    if elapsed:
        meta_bits.append(f"{elapsed}s")
    if pt:
        meta_bits.append(f"in:{pt:,}")
    if ct and substate in ("thinking", "writing"):
        meta_bits.append(f"out:{ct:,}")
    parts.append(f"[dim]`-[/dim] {_label(substate)} [bold blue]{sc}[/bold blue]{_meta(*meta_bits)}")

    show = buf if substate in ("thinking", "writing") else detail
    lines = [ln for ln in str(show or "").splitlines() if ln.strip()][-8:]
    if not lines and detail:
        lines = [detail]
    for j, ln in enumerate(lines):
        pfx = "  `-" if j == 0 else "    "
        parts.append(f"[dim]{pfx}[/dim] [dim]{_safe(ln)}[/dim]")

    return "\n".join(parts)


def render_curator_done(role: str, tok: str = "") -> str:
    head = f"[bold green]*[/bold green] [bold]{role}[/bold]{tok}"
    branches = []
    for i, s in enumerate(_ORDER):
        conn = "`-" if i == len(_ORDER) - 1 else "+-"
        branches.append(f"[dim]{conn}[/dim] {_label(s)} [green]OK[/green]")
    return "\n".join([head, *branches])
