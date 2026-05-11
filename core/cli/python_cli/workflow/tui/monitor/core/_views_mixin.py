"""Mixin: check-view and log-view open/close helpers."""
from __future__ import annotations

import re
from pathlib import Path

from ._utils import _r2a


class _ViewsMixin:
    def _open_check(self, root: str) -> None:
        try:
            from core.cli.python_cli.features.context.flow import find_context_md, is_no_context

            ctx = find_context_md(root)
            if not ctx or is_no_context(ctx):
                self._write("[dim]x No context.md found[/dim]")
                return
            self._open_file_view(
                ctx,
                title="context.md",
                footer=(
                    "[bold yellow]/accept[/bold yellow] accept  .  "
                    "[bold red]/delete[/bold red] reject  .  "
                    "[dim cyan]/edit[/dim cyan] open editor  .  "
                    "[dim]q/Esc close[/dim]"
                ),
            )
        except Exception as e:
            self._write(f"[red]x check error: {e}[/red]")

    def _open_file_view(self, path: str | Path, *, title: str | None = None, footer: str | None = None) -> None:
        p = Path(path)
        if not p.exists() or not p.is_file():
            self._write(f"[dim]x file not found: {p}[/dim]")
            return
        label = title or p.name
        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._write(f"[dim]x open failed: {exc}[/dim]")
            return

        safe_path = str(p).replace("[", r"\[")
        lines_raw = [_r2a(f"[bold]-- {label} --[/bold]  [dim]{safe_path}[/dim]")]
        for line in content.splitlines():
            lines_raw.append(_r2a(line.replace("[", r"\[")))
        lines_raw.append(_r2a("[dim]" + ("-" * 50) + "[/dim]"))
        lines_raw.append(_r2a(footer or "[dim]q/Esc close[/dim]"))

        self._check_lines = lines_raw
        self._check_scroll = 0
        self._check_ctx_path = str(p)
        self._check_edited = False
        self._check_mode = True
        if self._app:
            self._app.layout.focus(self._check_buffer)
            self._app.invalidate()

    def _close_check(self, *, silent: bool = False) -> None:
        self._check_mode = False
        self._check_lines = []
        if not silent and not self._log_mode:
            self._write("[dim]    |--[/dim] [dim]context.md opened[/dim]")
        if self._app:
            self._app.layout.focus(self._main_buffer)
            self._app.invalidate()

    def _open_log(self) -> None:
        try:
            from ....runtime.persist.activity_log import format_activity_lines, list_recent_activity

            records = list_recent_activity(limit=300)
            self._log_file_map = self._collect_log_files(records)

            lines_raw = [_r2a("[bold]-- activity log --[/bold]")]
            fmt_lines = format_activity_lines(records, "")
            if not fmt_lines:
                lines_raw.append(_r2a("[dim]  (no activity logged yet)[/dim]"))
            else:
                for line in fmt_lines:
                    lines_raw.append(_r2a(line))

            if self._log_file_map:
                lines_raw.append(_r2a("[dim]" + ("-" * 50) + "[/dim]"))
                lines_raw.append(_r2a("[bold]Files[/bold]  [dim]/open <name>[/dim]"))
                shown: set[str] = set()
                for name, path in sorted(self._log_file_map.items()):
                    if path in shown:
                        continue
                    shown.add(path)
                    safe_name = name.replace("[", r"\[")
                    safe_path = str(path).replace("[", r"\[")
                    lines_raw.append(_r2a(f"  [cyan]{safe_name}[/cyan]  [dim]{safe_path}[/dim]"))

            lines_raw.append(_r2a("[dim]" + ("-" * 50) + "[/dim]"))
            lines_raw.append(_r2a("[dim]  /open <file> . Esc / q to go back[/dim]"))
            self._log_lines = lines_raw
            self._log_scroll = 0
            self._log_mode = True
            if self._app:
                self._app.invalidate()
        except Exception as e:
            self._write(f"[dim]  (log error: {e})[/dim]")

    def _collect_log_files(self, records: list[dict]) -> dict[str, str]:
        found: dict[str, str] = {}
        for rec in records:
            detail = str(rec.get("detail", "") or "")
            match = re.search(r"(?:^|\s)path=(.+?)(?:\s+status=|$)", detail)
            raw_path = match.group(1).strip() if match else detail.strip()
            p = Path(raw_path)
            if not p.exists() or not p.is_file():
                continue
            path_s = str(p)
            found[p.name] = path_s
            found[path_s] = path_s
            try:
                found[str(p.relative_to(Path.cwd()))] = path_s
            except ValueError:
                pass
        return found

    def _open_log_file(self, query: str) -> None:
        q = str(query or "").strip().strip('"')
        if not q:
            self._log_lines.append(_r2a("[dim]  usage: /open <file>[/dim]"))
            if self._app:
                self._app.invalidate()
            return
        file_map = getattr(self, "_log_file_map", {}) or {}
        direct = file_map.get(q)
        if direct:
            self._open_file_view(direct, title=Path(direct).name, footer="[dim]q/Esc close . /back returns to log[/dim]")
            return

        matches: dict[str, str] = {}
        for name, path in file_map.items():
            if q.lower() in name.lower():
                matches[path] = name
        if len(matches) == 1:
            path = next(iter(matches))
            self._open_file_view(path, title=Path(path).name, footer="[dim]q/Esc close . /back returns to log[/dim]")
            return
        if matches:
            self._log_lines.append(_r2a(f"[yellow]multiple matches for {q}[/yellow]"))
            for idx, (path, name) in enumerate(matches.items(), 1):
                safe_name = name.replace("[", r"\[")
                safe_path = path.replace("[", r"\[")
                self._log_lines.append(_r2a(f"  {idx}. [cyan]{safe_name}[/cyan] [dim]{safe_path}[/dim]"))
        else:
            self._log_lines.append(_r2a(f"[dim]x no logged file matches: {q}[/dim]"))
        if self._app:
            self._app.invalidate()

    def _close_log(self) -> None:
        self._log_mode = False
        self._log_lines = []
        if self._app:
            self._app.invalidate()
