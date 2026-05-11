"""ASCII-safe Rich markup for workflow pipeline chain (monitor / Textual)."""

from __future__ import annotations

from typing import Callable

SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_MAX_PER_ROW = 4  # nodes per row before wrapping


def _glyph(visual: str, spin_char: str, spin_pulse: bool) -> str:
    if visual == "spin":
        # Braille spinner -- animated gray
        return f"[#888888]{spin_char}[/#888888]"
    if visual == "wait":
        return "[yellow]*◉[/yellow]"
    if visual == "done":
        return "[bold green]*[/bold green]"
    if visual == "error":
        return "[red]X[/red]"
    # pending -- static gray dot
    return "[grey46]o[/grey46]"


def _build_row(
    row_steps: list[str],
    states: dict[str, str],
    tier: str | None,
    selected_leader: str,
    spin_char: str,
    pulse: bool,
    display_name: Callable[[str], str],
    role_subtitle: Callable[[str, str | None, str], str],
    is_last_row: bool,
) -> tuple[str, str]:
    """Build one row of the pipeline chain (top + bottom lines)."""
    col_top: list[str] = []
    col_bottom: list[str] = []
    for sid in row_steps:
        g = _glyph(states.get(sid, "pending"), spin_char, pulse)
        name = display_name(sid)
        col_top.append(f"\\[ {g} [bold]{name}[/bold] ]")
        subtitle = role_subtitle(sid, tier, selected_leader)
        col_bottom.append(f"[dim]{subtitle}[/dim]" if subtitle else "[dim] [/dim]")

    sep = "  [dim white]---[/dim white]  "
    line1 = sep.join(col_top)

    if not is_last_row:
        line1 += "  [white]v[/white]"

    line2 = sep.join(col_bottom)
    return line1, line2


def build_pipeline_markup(
    steps: list[str],
    states: dict[str, str],
    tier: str | None,
    selected_leader: str,
    spin_idx: int,
    display_name: Callable[[str], str],
    role_subtitle: Callable[[str, str | None, str], str],
    active_detail: str | None = None,
    max_per_row: int = _MAX_PER_ROW,
) -> str:
    spin_char = SPINNER[spin_idx % len(SPINNER)]
    pulse = (spin_idx % 2) == 0

    if not steps:
        return "\n"

    # Chunk steps into rows
    rows: list[list[str]] = []
    for i in range(0, len(steps), max_per_row):
        rows.append(steps[i : i + max_per_row])

    row_markups: list[str] = []
    for r_idx, row_steps in enumerate(rows):
        is_last = r_idx == len(rows) - 1
        top, bottom = _build_row(
            row_steps, states, tier, selected_leader, spin_char, pulse,
            display_name, role_subtitle, is_last
        )
        row_markups.append(top)
        row_markups.append(bottom)

    result = "\n".join(row_markups)

    if active_detail:
        detail_str = active_detail.replace("\n", " ").strip()
        if len(detail_str) > 120:
            detail_str = detail_str[:117] + "..."
        result += f"\n[dim italic]{detail_str}[/dim italic]"

    return result


__all__ = ["SPINNER", "build_pipeline_markup", "_glyph", "_build_row"]
