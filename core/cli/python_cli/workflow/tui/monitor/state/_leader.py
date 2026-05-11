"""Leader state renderers: reading / thinking / writing tree."""
from __future__ import annotations

from core.cli.python_cli.i18n import t

_L_ORDER = ("reading", "thinking", "writing")


def _branch_label(s: str) -> str:
    return {
        "reading": t("unit.reading"),
        "thinking": t("unit.thinking"),
        "writing": t("unit.writing"),
    }.get(s, s)


def _meta(*vals) -> str:
    filt = [str(v) for v in vals if v]
    return f"  [dim]({'  '.join(filt)})[/dim]" if filt else ""


def _safe(text: object, limit: int = 98) -> str:
    return str(text or "").replace("[", "\\[")[:limit]


def render_leader_tree(sc: str, role: str, st: dict, elapsed: int = 0, tok: str = "") -> str:
    is_done = bool(st.get("is_done", False))
    attempt = int(st.get("attempt", 1) or 1)
    substate = str(st.get("substate") or "reading")
    detail = str(st.get("detail") or "")
    reasoning_acc = str(st.get("reasoning_acc") or "")
    reasoning_active = bool(st.get("reasoning_active", False))
    buf = str(st.get("buf") or "")
    pt = int(st.get("pt") or 0)
    ct = int(st.get("ct") or 0)
    r_pt = int(st.get("read_pt") or 0)

    if substate in ("generating", "idle", ""):
        substate = "thinking" if (buf or pt or ct or reasoning_acc or reasoning_active) else "reading"

    sc_part = "[bold green]*[/bold green]" if is_done else f"[#888888]{sc}[/#888888]"
    parts = [f"{sc_part} [bold]{role}[/bold]{tok if is_done else ''}"]

    if is_done:
        for i, s in enumerate(_L_ORDER):
            conn = "`-" if i == len(_L_ORDER) - 1 else "+-"
            parts.append(f"[dim]{conn}[/dim] {_branch_label(s)} [green]OK[/green]")
        return "\n".join(parts)

    try:
        cur_idx = _L_ORDER.index(substate)
    except ValueError:
        cur_idx = 1

    spin = f" [bold blue]{sc}[/bold blue]"
    for i, s in enumerate(_L_ORDER):
        conn = "`-" if i == cur_idx else "+-"
        if i < cur_idx:
            parts.append(f"[dim]{conn}[/dim] {_branch_label(s)} [green]OK[/green]")
            continue
        if i > cur_idx:
            continue

        if s == "reading":
            meta_s = _meta(
                f"{elapsed}s" if elapsed else "",
                f"in:{r_pt:,}" if r_pt else "",
                f"{t('unit.attempt')} {attempt}" if attempt > 1 else "",
            )
            parts.append(f"[dim]{conn}[/dim] {_branch_label(s)} [dim]{detail or 'state.json'}[/dim]{spin}{meta_s}")
        elif s == "thinking":
            meta_s = _meta(
                f"{elapsed}s" if elapsed else "",
                f"in:{pt:,}" if pt else "",
                f"out:{ct:,}" if ct else "",
                f"{t('unit.attempt')} {attempt}" if attempt > 1 else "",
            )
            parts.append(f"[dim]{conn}[/dim] {_branch_label(s)}{spin}{meta_s}")
            show = reasoning_acc or buf
            lines = [ln for ln in show.splitlines() if ln.strip() and "[CLARIFICATION]" not in ln][-30:]
            for j, ln in enumerate(lines):
                pfx = "  `-" if j == 0 else "    "
                parts.append(f"[dim]{pfx}[/dim] [dim]{_safe(ln)}[/dim]")
        else:
            meta_s = _meta(
                f"in:{pt:,}" if pt else "",
                f"out:{ct:,}" if ct else "",
                f"{t('unit.attempt')} {attempt}" if attempt > 1 else "",
            )
            parts.append(f"[dim]{conn}[/dim] {_branch_label(s)}{spin}{meta_s}")
            parts.append(f"  [dim]`-[/dim] [dim]{_safe(detail or 'context.md', 90)}[/dim]")

    return "\n".join(parts)


def render_regen_starting(sc: str, role: str, attempt: int) -> str:
    return render_leader_tree(
        sc,
        role,
        {"substate": "reading", "detail": "state.json", "attempt": attempt, "is_done": False},
    )
