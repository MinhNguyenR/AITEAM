from __future__ import annotations


def render_runtime_role_tree(sc: str, role: str, state: dict, elapsed: int = 0) -> str:
    substate = str(state.get("substate") or "running")
    detail = str(state.get("detail") or "")
    artifacts = list(state.get("artifacts") or [])
    lines = [
        f"{sc} [bold cyan]{role}[/bold cyan] [dim]{substate}[/dim]",
    ]
    if elapsed:
        lines.append(f"[dim]elapsed {elapsed}s[/dim]")
    if detail:
        lines.append(f"[white]{detail}[/white]")
    for artifact in artifacts[:3]:
        path = str(artifact.get("display_path") or artifact.get("path") or "")
        if path:
            lines.append(f"[dim]-> {path}[/dim]")
    return "\n".join(lines)


def render_runtime_role_done(role: str, detail: str = "", artifacts: list | None = None) -> str:
    lines = [f"[bold green]OK[/bold green] [bold]{role}[/bold]"]
    if detail:
        lines[0] += f"  [dim]{detail}[/dim]"
    for artifact in list(artifacts or [])[:4]:
        path = str(artifact.get("display_path") or artifact.get("path") or "")
        if path:
            lines.append(f"[dim]-> {path}[/dim]")
    return "\n".join(lines)


__all__ = ["render_runtime_role_tree", "render_runtime_role_done"]
