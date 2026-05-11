"""Static update/create diff renderers."""

from __future__ import annotations

def _safe(text: object) -> str:
    return str(text or "").replace("[", r"\[")


def _line(text: str, style: str = "white") -> str:
    return f"[{style}]{_safe(text)[:160]}[/{style}]"


def _chunk_diff_lines(diff_lines: list[dict], context: int = 6) -> list[list[dict]]:
    if not diff_lines:
        return []
    chunks: list[list[dict]] = []
    current: list[dict] = []
    last_num = None
    for item in diff_lines:
        num = item.get("num")
        changed = item.get("type") in {"add", "remove"}
        if current and changed and isinstance(num, int) and isinstance(last_num, int) and num - last_num > context:
            chunks.append(current)
            current = []
        current.append(item)
        if changed and isinstance(num, int):
            last_num = num
    if current:
        chunks.append(current)
    return chunks


def render_create_block(role: str, diff: dict) -> str:
    fp = _safe(diff.get("file_path", ""))
    content = str(diff.get("full_new_content") or "")
    lines = content.splitlines()
    shown = lines[:12]
    out = [
        f"[bold]* {role} - [green]Create[/green]([cyan]{fp}[/cyan])[/bold]",
        f"  [dim]-> Created ({len(lines)} lines)[/dim]",
    ]
    for idx, text in enumerate(shown, start=1):
        out.append(f"      [dim]{idx:<4}[/dim] {_line(text)}")
    if len(lines) > len(shown):
        out.append(f"      [dim]... {len(lines) - len(shown)} more lines[/dim]")
    return "\n".join(out)


def render_update_block(role: str, diff: dict) -> str:
    fp = _safe(diff.get("file_path", ""))
    added = int(diff.get("added") or 0)
    removed = int(diff.get("removed") or 0)
    out = [
        f"[bold]* {role} - [yellow]Update[/yellow]([cyan]{fp}[/cyan])[/bold]",
        f"  [dim]-> Added {added} line{'s' if added != 1 else ''}, Removed {removed} line{'s' if removed != 1 else ''}[/dim]",
    ]
    chunks = _chunk_diff_lines(list(diff.get("diff_lines") or []), context=6)
    for ci, chunk in enumerate(chunks):
        if ci:
            out.append("      [dim]...[/dim]")
        for item in chunk:
            typ = item.get("type")
            num = item.get("num")
            text = str(item.get("text") or "")
            n = "    " if num is None else f"{int(num):<4}"
            if typ == "add":
                out.append(f"      [dim]{n}[/dim] [green]+ {_safe(text)[:150]}[/green]")
            elif typ == "remove":
                out.append(f"      [dim]{n}[/dim] [red]- {_safe(text)[:150]}[/red]")
            else:
                out.append(f"      [dim]{n}[/dim] {_line(text)}")
    return "\n".join(out)


__all__ = ["_chunk_diff_lines", "render_create_block", "render_update_block"]
