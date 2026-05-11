"""Ambassador state renderers."""
from __future__ import annotations

from core.cli.python_cli.i18n import t

_A_ORDER = ("reading", "thinking", "writing")
_BRANCH = "\u251c\u2500"
_LAST = "\u2514\u2500"
_DOT = "\u25cf"
_CHECK = "\u2713"

_LABELS = {
    "reading": lambda: t("unit.reading"),
    "thinking": lambda: t("unit.thinking"),
    "writing": lambda: t("unit.writing"),
}


def render_running(
    sc: str,
    role: str,
    buf: str,
    pt: int,
    ct: int,
    attempt: int,
    elapsed: int = 0,
    reasoning_acc: str = "",
    reasoning_active: bool = False,
    substate: str = "",
    detail: str = "",
) -> str:
    del reasoning_active
    if not substate or substate not in _A_ORDER:
        substate = "thinking"

    try:
        cur_idx = _A_ORDER.index(substate)
    except ValueError:
        cur_idx = 1

    parts = [f"[#888888]{sc}[/#888888] [bold]{role}[/bold]"]
    spin = f" [bold blue]{sc}[/bold blue]"

    for i, s in enumerate(_A_ORDER):
        label = _LABELS[s]()
        conn = f"[dim]{_LAST}[/dim]" if i == cur_idx else f"[dim]{_BRANCH}[/dim]"

        if i < cur_idx:
            parts.append(f"{conn} {label} [green]{_CHECK}[/green]")
            continue
        if i > cur_idx:
            continue

        meta_bits: list[str] = []
        if elapsed > 0:
            meta_bits.append(f"{elapsed}s")
        if s == "thinking" and (pt or ct):
            meta_bits.append(f"{t('unit.token_in')}: {pt:,} {t('unit.token_out')}: {ct:,}")
        if attempt > 1:
            meta_bits.append(f"{t('unit.attempt')} {attempt}")
        meta_s = f"  [dim]({', '.join(meta_bits)})[/dim]" if meta_bits else ""
        parts.append(f"{conn} {label}{spin}{meta_s}")

        if s == "reading":
            det = detail or "User input"
            safe = det.replace("[", r"\[")
            parts.append(f"  [dim]{_LAST}[/dim] [dim]{safe[:94]}[/dim]")
        elif s == "thinking":
            show = reasoning_acc or buf
            lines = [
                ln for ln in show.split("\n")
                if ln.strip() and "[CLARIFICATION]" not in ln and "[/CLARIFICATION]" not in ln
            ][-12:]
            for j, ln in enumerate(lines):
                pfx = f"[dim]  {_LAST}[/dim]" if j == 0 else "[dim]    [/dim]"
                safe = ln.replace("[", r"\[")
                parts.append(f"{pfx} [dim]{safe[:98]}[/dim]")
        elif s == "writing":
            det = detail or "state.json"
            safe = det.replace("[", r"\[")
            parts.append(f"  [dim]{_LAST}[/dim] [dim]{safe[:94]}[/dim]")
            lines = [ln for ln in buf.split("\n") if ln.strip()][-6:]
            for j, ln in enumerate(lines):
                pfx = f"[dim]    {_LAST}[/dim]" if j == 0 else "[dim]      [/dim]"
                safe_ln = ln.replace("[", r"\[")
                parts.append(f"{pfx} [dim]{safe_ln[:94]}[/dim]")

    return "\n".join(parts)


def render_done(role: str, tok: str) -> str:
    """All branches shown with checks, no detail sub-branches."""
    if "in:" in tok:
        tok = tok.replace("in:", f"{t('unit.token_in')}:").replace("out:", f"{t('unit.token_out')}:")
    lines = [f"[bold green]{_DOT}[/bold green] [bold]{role}[/bold]{tok}"]
    for i, s in enumerate(_A_ORDER):
        conn = _LAST if i == len(_A_ORDER) - 1 else _BRANCH
        lines.append(f"[dim]{conn}[/dim] {_LABELS[s]()} [green]{_CHECK}[/green]")
    return "\n".join(lines)
