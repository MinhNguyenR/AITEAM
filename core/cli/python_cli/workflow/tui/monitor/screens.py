"""Modal screens for the workflow monitor TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult, on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, RichLog, Static

from core.cli.python_cli.features.context.flow import find_context_md, is_no_context
from core.cli.python_cli.shell.safe_editor import run_editor_on_file
from core.app_state import log_system_action
from core.cli.python_cli.i18n import t

from ...runtime.persist.activity_log import format_activity_lines, list_recent_activity
from ...runtime import session as ws
from .helpers import (
    _activity_min_ts_kw,
    _checkpoint_blocks,
)


class CheckpointSearchScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", t("ui.close"), show=False)]

    def __init__(self, needle: str) -> None:
        super().__init__()
        self._needle = needle

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]search[/bold] {self._needle or '(all)'}  [dim]{t('ui.esc_close')}[/dim]", id="search_hdr")
        with VerticalScroll():
            yield RichLog(id="search_log", highlight=True, markup=True, wrap=True)

    def on_mount(self) -> None:
        log = self.query_one("#search_log", RichLog)
        for block in _checkpoint_blocks(self._needle):
            log.write(block)
            log.write("")

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class ActivityLogScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", t("ui.close"), show=False)]

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]workflow_activity.log[/bold] ({t('dash.history_label_short').format(n=1)})  [dim]Esc[/dim]")
        with VerticalScroll():
            yield RichLog(id="full_log", highlight=True, markup=True, wrap=True)

    def on_mount(self) -> None:
        log = self.query_one("#full_log", RichLog)
        for line in format_activity_lines(list_recent_activity(limit=300, min_ts=_activity_min_ts_kw()), ""):
            log.write(line)

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class ContextFilePreviewScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", t("ui.close"), show=False)]

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]{self._path}[/bold]  [dim]Esc[/dim]")
        with VerticalScroll():
            yield RichLog(id="prev_log", highlight=True, markup=True, wrap=True)

    def on_mount(self) -> None:
        log = self.query_one("#prev_log", RichLog)
        p = Path(self._path)
        if not p.is_file():
            log.write(f"[red]{t('ui.file_not_found')}[/red]")
            return
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            log.write(f"[red]{e}[/red]")
            return
        lines = text.splitlines()
        head = "\n".join(lines[:150])
        if len(lines) > 150:
            head += f"\n\n[dim]… {t('context.lines_hidden').format(n=len(lines)-150)}[/dim]"
        log.write(head)

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class RegeneratePromptScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", t("ui.close"), show=False)]

    def __init__(self, project_root: str) -> None:
        super().__init__()
        self._project_root = project_root

    def compose(self) -> ComposeResult:
        yield Static(t("context.regen_title"))
        yield Input(id="regen_input", placeholder=t("context.regen_placeholder"))

    @on(Input.Submitted, "#regen_input")
    def _sub(self, event: Input.Submitted) -> None:
        t_val = (event.value or "").strip()
        event.input.value = ""
        if t_val:
            ws.enqueue_monitor_command(
                "context_regenerate",
                {"project_root": self._project_root, "prompt": t_val},
            )
            log_system_action("monitor.cmd", "context_regenerate")
            self.notify(t("context.sent_notify"), timeout=5)
        self.dismiss()

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class ContextReviewScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", t("ui.close"), show=False)]

    def __init__(self, project_root: str) -> None:
        super().__init__()
        self._project_root = project_root

    def compose(self) -> ComposeResult:
        yield Static(id="ctx_title")
        with VerticalScroll():
            yield Static(id="ctx_md")
        yield Horizontal(
            Button(t("context.accept_desc").split(" — ")[0], id="b_a", variant="success"),
            Button(t("context.edit_desc").split(" — ")[0], id="b_e"),
            Button(t("context.regen_desc").split(" — ")[0], id="b_r"),
            Button(t("nav.back").split(" ")[0].title(), id="b_b"),
            Button(t("context.delete_desc").split(" — ")[0], id="b_d", variant="error"),
        )

    def on_mount(self) -> None:
        ctx = find_context_md(self._project_root)
        title = self.query_one("#ctx_title", Static)
        body = self.query_one("#ctx_md", Static)
        if not ctx:
            title.update(f"[red]{t('context.not_found')}[/red]")
            body.update("")
            return
        if is_no_context(ctx):
            title.update(f"[red]{t('context.sentinel')}[/red]")
            body.update("")
            return
        title.update(str(ctx))
        content = ctx.read_text(encoding="utf-8")
        lines = content.splitlines()
        preview = "\n".join(lines[:120])
        if len(lines) > 120:
            preview += f"\n\n[dim]{t('context.lines_hidden').format(n=len(lines)-120)}[/dim]"
        body.update(preview)

    @on(Button.Pressed, "#b_a")
    def _accept(self) -> None:
        root = self._project_root
        ws.enqueue_monitor_command("context_accept", {"project_root": root})
        log_system_action("monitor.cmd", "context_accept")
        self.notify(t("context.accept_notify"), timeout=5)
        self.dismiss()

    @on(Button.Pressed, "#b_e")
    def _edit(self) -> None:
        ctx = find_context_md(self._project_root)
        if not ctx:
            self.notify(t("ui.file_not_found"), severity="error")
            return
        run_editor_on_file(ctx)
        self.notify(t("context.edit_notify"), timeout=4)

    @on(Button.Pressed, "#b_r")
    def _regen(self) -> None:
        self.app.push_screen(RegeneratePromptScreen(self._project_root))

    @on(Button.Pressed, "#b_b")
    def _back(self) -> None:
        ws.enqueue_monitor_command("context_back", {"project_root": self._project_root})
        log_system_action("monitor.cmd", "context_back")
        self.notify(t("context.back_notify"), timeout=4)
        self.dismiss()

    @on(Button.Pressed, "#b_d")
    def _delete(self) -> None:
        ws.enqueue_monitor_command("context_delete", {"project_root": self._project_root})
        log_system_action("monitor.cmd", "context_delete")
        self.notify(t("context.delete_notify"), timeout=5)
        self.dismiss()

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class ConfirmExitScreen(ModalScreen[bool]):
    """Confirmation modal when user exits during an active workflow run."""

    BINDINGS = [Binding("escape", "cancel", t("ui.cancelled"), show=False)]

    CSS = """
    ConfirmExitScreen {
        align: center middle;
    }
    #exit_container {
        width: 66;
        height: auto;
        background: #1e2030;
        border: solid #f7768e;
        padding: 1 2;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="exit_container"):
            yield Static(
                f"[bold red]{t('exit.warn_running')}[/bold red]\n\n"
                f"[yellow]{t('exit.warn_desc')}[/yellow]\n"
                f"[dim]{t('exit.artifact_removal')}[/dim]"
            )
            yield Horizontal(
                Button(t("exit.cancel_keep"), id="b_cancel", variant="primary"),
                Button(t("exit.exit_clean"), id="b_exit", variant="error"),
            )

    @on(Button.Pressed, "#b_cancel")
    def _cancel(self) -> None:
        self.dismiss(False)

    @on(Button.Pressed, "#b_exit")
    def _exit(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class DeleteConfirmScreen(ModalScreen[str | None]):
    """Push after context delete — lets user enter a new task inline before exiting."""

    BINDINGS = [Binding("escape", "cancel", t("del.no_regen"), show=False)]

    CSS = """
    DeleteConfirmScreen {
        align: center middle;
    }
    #del_container {
        width: 64;
        height: auto;
        background: #1e2030;
        border: solid #e0af68;
        padding: 1 2;
    }
    """

    def __init__(self, project_root: str) -> None:
        super().__init__()
        self._project_root = project_root

    def compose(self) -> ComposeResult:
        with Vertical(id="del_container"):
            yield Static(
                f"[bold yellow]● {t('context.deleted')}[/bold yellow]\n"
                f"[dim]{t('context.regen_title')}[/dim]"
            )
            yield Input(id="del_input", placeholder=t("context.regen_placeholder"))

    def on_mount(self) -> None:
        try:
            self.query_one("#del_input", Input).focus()
        except LookupError:
            pass

    @on(Input.Submitted, "#del_input")
    def _submit(self, event: Input.Submitted) -> None:
        t_val = (event.value or "").strip()
        self.dismiss(t_val if t_val else None)

    def action_cancel(self) -> None:
        self.dismiss(None)


__all__ = [
    "ActivityLogScreen",
    "CheckpointSearchScreen",
    "ConfirmExitScreen",
    "ContextFilePreviewScreen",
    "ContextReviewScreen",
    "DeleteConfirmScreen",
    "RegeneratePromptScreen",
]
