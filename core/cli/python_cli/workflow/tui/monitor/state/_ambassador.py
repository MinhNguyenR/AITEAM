"""Ambassador state renderers — running and done."""
from __future__ import annotations
from core.cli.python_cli.i18n import t


def render_running(
    sc: str, role: str, buf: str, pt: int, ct: int, attempt: int, elapsed: int = 0,
    reasoning_acc: str = '', reasoning_active: bool = False,
) -> str:
    meta: list[str] = []
    if elapsed > 0:
        meta.append(f"{elapsed}s")
    if pt or ct:
        meta.append(f"{t('unit.token_in')}: {pt:,} {t('unit.token_out')}: {ct:,}")
    if attempt > 1:
        meta.append(f"{t('unit.attempt')} {attempt}")
    meta_s = f"  [dim]({', '.join(meta)})[/dim]" if meta else ""

    parts = [f"[#888888]{sc}[/#888888] [bold]{role}[/bold]"]

    has_reasoning = bool(reasoning_acc)
    if has_reasoning:
        # Show reasoning branch while it's active; then generation branch after
        parts.append(f"[dim]├─[/dim] {t('pipeline.generating')}{meta_s}")
        dot = f" [bold blue]{sc}[/bold blue]" if reasoning_active else " [green]✓[/green]"
        r_lines = [ln for ln in reasoning_acc.split("\n") if ln.strip()]
        parts.append(f"[dim]└─[/dim] {t('unit.reasoning')}{dot}")
        for i, ln in enumerate(r_lines[-4:]):
            pfx = "[dim]  └─[/dim]" if i == 0 else "[dim]    [/dim]"
            safe = ln.replace("[", "\\[")
            parts.append(f"{pfx} [dim]{safe[:94]}[/dim]")
    else:
        parts.append(f"[dim]└─[/dim] {t('pipeline.generating')}{meta_s}")
        buf_lines = [ln for ln in buf.split("\n") if ln.strip()] if buf else []
        for i, ln in enumerate(buf_lines[-6:]):
            pfx = "[dim]  └─[/dim]" if i == 0 else "[dim]    [/dim]"
            safe = ln.replace("[", "\\[")
            parts.append(f"{pfx} [dim]{safe[:98]}[/dim]")
    return "\n".join(parts)


def render_done(role: str, tok: str) -> str:
    """Green-dot completed display — stays visible in live section while leader runs."""
    # format of tok is expected to be  [dim](in:X out:Y)[/dim]
    # we replace in: out: with localized token in: token out:
    if "in:" in tok:
        tok = tok.replace("in:", f"{t('unit.token_in')}:").replace("out:", f"{t('unit.token_out')}:")
    return (
        f"[bold green]●[/bold green] [bold]{role}[/bold]\n"
        f"[dim]└─[/dim] {t('pipeline.generating')} ✓{tok}"
    )
