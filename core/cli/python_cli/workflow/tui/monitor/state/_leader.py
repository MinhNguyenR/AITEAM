"""Leader state renderers — reading, reasoning, generating/regenerating."""
from __future__ import annotations
from core.cli.python_cli.i18n import t


def render_leader_tree(sc: str, role: str, st: dict, elapsed: int = 0) -> str:
    """Unified leader live-display tree.

    st keys: substate, read_pt, read_elapsed, reasoning_acc, reasoning_active,
             buf, pt, ct, attempt, is_done
    """
    is_done          = st.get('is_done', False)
    attempt          = st.get('attempt', 1)
    substate         = st.get('substate', 'generating')
    reasoning_acc    = st.get('reasoning_acc', '')
    reasoning_active = st.get('reasoning_active', False)
    has_reasoning    = bool(reasoning_acc)

    sc_part = "[bold green]●[/bold green]" if is_done else f"[#888888]{sc}[/#888888]"
    parts   = [f"{sc_part} [bold]{role}[/bold]"]

    def _meta(*vals) -> str:
        filt = [str(v) for v in vals if v]
        return f"  [dim]({'  '.join(filt)})[/dim]" if filt else ""

    # ── 1. Reading (attempt 1 only) ───────────────────────────────────────────
    if attempt == 1:
        r_pt   = st.get('read_pt', 0)
        r_elap = st.get('read_elapsed', 0)

        if substate == 'reading' and not has_reasoning:
            meta = _meta(
                f"{elapsed}s" if elapsed else "",
                f"in:{r_pt:,}" if r_pt else "",
            )
            parts.append(f"[dim]└─[/dim] {t('info.reading_file').format(f='state.json')}{meta}")
            return "\n".join(parts)

        # Reading done
        meta = _meta(
            f"{r_elap}s" if r_elap else "",
            f"in:{r_pt:,}" if r_pt else "",
        )
        parts.append(f"[dim]├─[/dim] {t('info.reading_file').format(f='state.json')}{meta} [green]✓[/green]")

    # ── 2. Reasoning — visible whenever the model produces reasoning tokens ───
    if has_reasoning:
        r_lines = [ln for ln in reasoning_acc.split("\n") if ln.strip()]
        r_ct    = st.get('ct', 0)
        # Blue spinning dot when active, green ✓ when done
        dot    = f" [bold blue]{sc}[/bold blue]" if reasoning_active else " [green]✓[/green]"
        meta   = _meta(
            f"{elapsed}s" if elapsed else "",
            f"out:{r_ct:,}" if r_ct else "",
        )
        parts.append(f"[dim]└─[/dim] {t('unit.reasoning')}{dot}{meta}")
        for i, ln in enumerate(r_lines[-5:]):
            pfx  = "[dim]  └─[/dim]" if i == 0 else "[dim]    [/dim]"
            safe = ln.replace("[", "\\[")
            parts.append(f"{pfx} [dim]{safe[:94]}[/dim]")
        return "\n".join(parts)

    # ── 3. Generating / regenerating ─────────────────────────────────────────
    label_key = 'info.regenerate_file' if attempt > 1 else 'info.generate_file'
    label     = t(label_key).format(f='context.md')
    
    g_pt   = st.get('pt', 0)
    g_ct   = st.get('ct', 0)
    g_meta = []
    if not is_done and elapsed: g_meta.append(f"{elapsed}s")
    if g_pt: g_meta.append(f"in:{g_pt:,}")
    if g_ct: g_meta.append(f"out:{g_ct:,}")
    if attempt > 1: g_meta.append(f"{t('unit.attempt')} {attempt}")
    meta_s = f"  [dim]({'  '.join(g_meta)})[/dim]" if g_meta else ""
    check  = " [green]✓[/green]" if is_done else ""

    parts.append(f"[dim]└─[/dim] {label}{meta_s}{check}")

    if not is_done:
        buf       = st.get('buf', '')
        buf_lines = [ln for ln in buf.split("\n") if ln.strip()] if buf else []
        # Skip model preamble — only show from first # heading
        start = None
        for idx, ln in enumerate(buf_lines):
            if ln.lstrip().startswith('#'):
                start = idx
                break
        if start is not None:
            for i, ln in enumerate(buf_lines[start:][-5:]):
                pfx  = "[dim]  └─[/dim]" if i == 0 else "[dim]    [/dim]"
                safe = ln.replace("[", "\\[")
                parts.append(f"{pfx} [dim]{safe[:98]}[/dim]")

    return "\n".join(parts)


def render_regen_starting(sc: str, role: str, attempt: int) -> str:
    """Shown during idle gap while pipeline restarts for regen."""
    return (
        f"[#888888]{sc}[/#888888] [bold]{role}[/bold]\n"
        f"[dim]└─[/dim] {t('info.regenerate_file').format(f='context.md')}…  [dim]({t('unit.attempt')} {attempt})[/dim]"
    )
