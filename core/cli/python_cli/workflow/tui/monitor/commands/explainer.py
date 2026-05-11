"""Explainer inline command handler."""
from __future__ import annotations

import threading


def handle_explainer_inline(app, payload: str, root: str) -> None:
    def _run() -> None:
        try:
            from agents.explainer import Explainer
            from core.app_state import get_cli_settings

            exp = Explainer()
            parts = [p for p in payload.strip().split() if p]
            lang = str(get_cli_settings().get("display_language") or "vi")
            if parts and parts[0] == "@codebase":
                selected = exp.select_codebase_files(root, limit=12)
                app._safe_ui(lambda: app._write(
                    f"[bold cyan]Explainer[/bold cyan] chọn tối đa 12 file; đã chọn {len(selected)} file."
                ))
                result = (
                    exp.annotate_files(selected, root, task_uuid="explainer", display_language=lang)
                    if selected
                    else {"files_written": [], "errors": ["no files selected"]}
                )
            else:
                file_args = parts[1:] if parts and parts[0] == "@file" else [p.lstrip("@") for p in parts]
                if not file_args:
                    app._safe_ui(lambda: app._write(
                        "[yellow]Chưa có file chỉ định. Dùng /explainer @file path/to/file.py[/yellow]"
                    ))
                    return
                result = exp.annotate_files(file_args, root, task_uuid="explainer", display_language=lang)
            changed = len(result.get("files_written", []))
            errors = result.get("errors", [])

            def _show() -> None:
                app._write(f"[bold green]Explainer[/bold green] updated {changed} file(s).")
                if errors:
                    app._write(f"[yellow]{len(errors)} issue(s): {errors[:3]}[/yellow]")
                if app._app:
                    app._app.invalidate()

            app._safe_ui(_show)
        except Exception as exc:
            app._safe_ui(lambda: app._write(f"[red]Explainer error: {exc}[/red]"))

    threading.Thread(target=_run, daemon=True).start()
