"""Secretary state renderer."""
from __future__ import annotations

from core.cli.python_cli.i18n import t

_ORDER = ("asking", "using", "fallback")
_BRANCH = "\u251c\u2500"
_LAST = "\u2514\u2500"
_DOT = "\u25cf"
_CHECK = "\u2713"
_CROSS = "\u2717"


def _label(substate: str) -> str:
    return {
        "reading": t("unit.reading"),
        "asking": t("unit.asking"),
        "using": t("unit.using"),
        "fallback": t("unit.fallback"),
    }.get(substate, substate)


def render_secretary_tree(sc: str, role: str, st: dict, elapsed: int = 0) -> str:
    """Render the Secretary live tree."""
    is_done = bool(st.get("is_done"))
    substate = str(st.get("substate") or "asking")
    detail = str(st.get("detail") or "")
    cmd_results = list(st.get("command_results") or [])

    sc_part = f"[bold green]{_DOT}[/bold green]" if is_done else f"[#888888]{sc}[/#888888]"
    parts = [f"{sc_part} [bold]{role}[/bold]"]

    if is_done:
        passed = sum(1 for c in cmd_results if c.get("success"))
        total = len(cmd_results)
        summary = f"  [dim]({passed}/{total} passed)[/dim]" if total else ""
        parts[-1] += summary
        done_steps = ["asking"] if total == 0 else ["using"]
        for i, s in enumerate(done_steps):
            connector = _LAST if i == len(done_steps) - 1 else _BRANCH
            parts.append(f"[dim]{connector}[/dim] {_label(s)} [green]{_CHECK}[/green]")
        return "\n".join(parts)

    try:
        cur_idx = _ORDER.index(substate)
    except ValueError:
        cur_idx = 0

    for s in _ORDER[:cur_idx]:
        if s == "fallback":
            continue
        parts.append(f"[dim]{_BRANCH}[/dim] {_label(s)} [green]{_CHECK}[/green]")

    spin = f" [bold blue]{sc}[/bold blue]"
    elapsed_str = f"  [dim]({elapsed}s)[/dim]" if elapsed else ""
    parts.append(f"[dim]{_LAST}[/dim] {_label(substate)}{spin}{elapsed_str}")

    if substate == "asking" and detail:
        safe = detail.replace("[", r"\[")
        parts.append(f"  [dim]{_LAST}[/dim] [dim]{safe[:88]}[/dim]")
    elif substate == "using" and detail:
        safe = detail.replace("[", r"\[")
        parts.append(f"  [dim]{_LAST}[/dim] [dim]$ {safe[:88]}[/dim]")
    elif substate == "fallback" and detail:
        safe = detail.replace("[", r"\[")
        parts.append(f"  [dim]{_LAST}[/dim] [dim]retry: {safe[:84]}[/dim]")

    if cmd_results:
        last = cmd_results[-1]
        icon = f"[green]{_CHECK}[/green]" if last.get("success") else f"[red]{_CROSS}[/red]"
        cmd_safe = str(last.get("cmd", "")).replace("[", r"\[")[:60]
        parts.append(f"  [dim]  [/dim] {icon} [dim]{cmd_safe}[/dim]")

    return "\n".join(parts)


def render_secretary_done(role: str, passed: int = 0, total: int = 0) -> str:
    summary = f"  [dim]({passed}/{total} passed)[/dim]" if total else ""
    head = f"[bold green]{_DOT}[/bold green] [bold]{role}[/bold]{summary}"
    branches = [
        f"[dim]{_LAST}[/dim] {_label('using' if total else 'asking')} [green]{_CHECK}[/green]",
    ]
    return "\n".join([head, *branches])
