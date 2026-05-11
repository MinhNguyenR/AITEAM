"""Worker state renderer -- reading -> thinking -> [asking] -> writing -> [using]."""

from __future__ import annotations

from core.cli.python_cli.i18n import t

_ORDER = ("reading", "thinking", "asking", "writing", "using")


def _label(substate: str) -> str:
    return {
        "reading": t("unit.reading"),
        "thinking": t("unit.thinking"),
        "asking": t("unit.asking"),
        "writing": t("unit.writing"),
        "using": t("unit.using"),
    }.get(substate, substate)


def _meta(*vals: str) -> str:
    filt = [str(v) for v in vals if v]
    return f"  [dim]({'  '.join(filt)})[/dim]" if filt else ""


def render_worker_tree(sc: str, role: str, st: dict, elapsed: int = 0) -> str:
    """Render the Worker live tree.

    st keys: substate, detail, reading_files, using_cmd, command_results, pt, ct, buf, is_done
    """
    is_done = bool(st.get("is_done"))
    substate = str(st.get("substate") or "reading")
    detail = str(st.get("detail") or "")
    reading_files = list(st.get("reading_files") or [])

    using_cmd = str(st.get("using_cmd") or "")

    pt = int(st.get("pt") or 0)

    ct = int(st.get("ct") or 0)

    buf = str(st.get("buf") or "")

    sc_part = "[bold green]*[/bold green]" if is_done else f"[#888888]{sc}[/#888888]"

    parts = [f"{sc_part} [bold]{role}[/bold]"]

    if is_done:
        visible = [s for s in _ORDER if s != "asking"]

        for i, s in enumerate(visible):
            connector = "+-" if i == len(visible) - 1 else "+-"

            parts.append(f"[dim]{connector}[/dim] {_label(s)} [green]OK[/green]")

        return "\n".join(parts)

    try:
        cur_idx = _ORDER.index(substate)

    except ValueError:
        cur_idx = 0

    for i, s in enumerate(_ORDER[:cur_idx]):
        if s == "asking" and substate != "asking":
            continue

        parts.append(f"[dim]+-[/dim] {_label(s)} [green]OK[/green]")

    spin = f" [bold blue]{sc}[/bold blue]"

    meta_bits: list[str] = []

    if elapsed:
        meta_bits.append(f"{elapsed}s")

    if substate in ("thinking", "writing") and pt:
        meta_bits.append(f"in:{pt:,}")

    if substate in ("thinking", "writing") and ct:
        meta_bits.append(f"out:{ct:,}")

    meta = _meta(*meta_bits)

    parts.append(f"[dim]+-[/dim] {_label(substate)}{spin}{meta}")

    if substate == "reading" and reading_files:
        for j, fp in enumerate(reading_files[-4:]):
            pfx = "[dim]  +-[/dim]" if j == 0 else "[dim]    [/dim]"

            safe = fp.replace("[", r"\[")

            parts.append(f"{pfx} [dim]{safe[:90]}[/dim]")

    elif substate == "thinking" and buf:
        lines_all = [ln for ln in buf.split("\n") if ln.strip()]

        lines = lines_all

        if len(lines_all) > 30:
            hidden = len(lines_all) - 30

            parts.append(f"[dim]  +-[/dim] [dim]^ {hidden} more lines above[/dim]")

            lines = lines_all[-30:]

        for j, ln in enumerate(lines):
            pfx = "[dim]  +-[/dim]" if j == 0 else "[dim]    [/dim]"

            safe = ln.replace("[", r"\[")

            parts.append(f"{pfx} [dim]{safe[:94]}[/dim]")

    elif substate == "writing" and detail:
        safe = detail.replace("[", r"\[")

        parts.append(f"  [dim]+-[/dim] [dim]{safe[:90]}[/dim]")

        if buf:
            for j, ln in enumerate([ln for ln in buf.split("\n") if ln.strip()][-6:]):
                pfx = "[dim]    `-[/dim]" if j == 0 else "[dim]      [/dim]"

                safe_ln = ln.replace("[", r"\[")

                parts.append(f"{pfx} [dim]{safe_ln[:94]}[/dim]")

    elif substate == "using" and using_cmd:
        safe = using_cmd.replace("[", r"\[")

        parts.append(f"  [dim]+-[/dim] [dim]$ {safe[:88]}[/dim]")

    elif detail:
        safe = detail.replace("[", r"\[")

        parts.append(f"  [dim]+-[/dim] [dim]{safe[:90]}[/dim]")

    return "\n".join(parts)


def render_worker_done(role: str, files_written: int = 0, tok: str = "") -> str:

    head = f"[bold green]*[/bold green] [bold]{role}[/bold]"

    if files_written:
        head += f"  [dim]({files_written} files)[/dim]"

    if tok:
        head += tok

    visible = [s for s in _ORDER if s != "asking"]

    branches = []

    for i, s in enumerate(visible):
        connector = "+-" if i == len(visible) - 1 else "+-"

        branches.append(f"[dim]{connector}[/dim] {_label(s)} [green]OK[/green]")

    return "\n".join([head, *branches])
