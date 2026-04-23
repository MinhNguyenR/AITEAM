"""Modal screens for the workflow monitor TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult, on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, RichLog, Static

from core.cli.flows.context_flow import find_context_md, is_no_context
from core.cli.safe_editor import run_editor_on_file
from core.cli.state import log_system_action

from ..runtime.activity_log import format_activity_lines, list_recent_activity
from ..runtime import session as ws
from .monitor_helpers import (
    _activity_min_ts_kw,
    _checkpoint_blocks,
)


class CheckpointSearchScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", "Đóng", show=False)]

    def __init__(self, needle: str) -> None:
        super().__init__()
        self._needle = needle

    def compose(self) -> ComposeResult:
        yield Static(f"[bold]search[/bold] {self._needle or '(all)'}  [dim]Esc đóng[/dim]", id="search_hdr")
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
    BINDINGS = [Binding("escape", "dismiss", "Đóng", show=False)]

    def compose(self) -> ComposeResult:
        yield Static("[bold]workflow_activity.log[/bold] (gần nhất)  [dim]Esc[/dim]")
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
    BINDINGS = [Binding("escape", "dismiss", "Đóng", show=False)]

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
            log.write("[red]File không tồn tại.[/red]")
            return
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            log.write(f"[red]{e}[/red]")
            return
        lines = text.splitlines()
        head = "\n".join(lines[:150])
        if len(lines) > 150:
            head += f"\n\n[dim]… {len(lines) - 150} dòng ẩn[/dim]"
        log.write(head)

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class RegeneratePromptScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", "Đóng", show=False)]

    def __init__(self, project_root: str) -> None:
        super().__init__()
        self._project_root = project_root

    def compose(self) -> ComposeResult:
        yield Static("Task mới (regenerate) — Enter gửi, Esc hủy")
        yield Input(id="regen_input", placeholder="Nhập task…")

    @on(Input.Submitted, "#regen_input")
    def _sub(self, event: Input.Submitted) -> None:
        t = (event.value or "").strip()
        event.input.value = ""
        if t:
            ws.enqueue_monitor_command(
                "context_regenerate",
                {"project_root": self._project_root, "prompt": t},
            )
            log_system_action("monitor.cmd", "context_regenerate")
            self.notify("Đã gửi — quay CLI menu để chạy.", timeout=5)
        self.dismiss()

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class ContextReviewScreen(ModalScreen[None]):
    BINDINGS = [Binding("escape", "dismiss", "Đóng", show=False)]

    def __init__(self, project_root: str) -> None:
        super().__init__()
        self._project_root = project_root

    def compose(self) -> ComposeResult:
        yield Static(id="ctx_title")
        with VerticalScroll():
            yield Static(id="ctx_md")
        yield Horizontal(
            Button("Accept", id="b_a", variant="success"),
            Button("Edit", id="b_e"),
            Button("Regenerate", id="b_r"),
            Button("Back", id="b_b"),
            Button("Delete", id="b_d", variant="error"),
        )

    def on_mount(self) -> None:
        ctx = find_context_md(self._project_root)
        title = self.query_one("#ctx_title", Static)
        body = self.query_one("#ctx_md", Static)
        if not ctx:
            title.update("[red]Không tìm thấy context.md[/red]")
            body.update("")
            return
        if is_no_context(ctx):
            title.update("[red]NO_CONTEXT sentinel[/red]")
            body.update("")
            return
        title.update(str(ctx))
        content = ctx.read_text(encoding="utf-8")
        lines = content.splitlines()
        preview = "\n".join(lines[:120])
        if len(lines) > 120:
            preview += f"\n\n… ({len(lines) - 120} dòng ẩn)"
        body.update(preview)

    @on(Button.Pressed, "#b_a")
    def _accept(self) -> None:
        root = self._project_root
        ws.enqueue_monitor_command("context_accept", {"project_root": root})
        log_system_action("monitor.cmd", "context_accept")
        self.notify("Accept đã gửi — quay CLI để thực thi resume.", timeout=5)
        self.dismiss()

    @on(Button.Pressed, "#b_e")
    def _edit(self) -> None:
        ctx = find_context_md(self._project_root)
        if not ctx:
            self.notify("Không có file.", severity="error")
            return
        run_editor_on_file(ctx)
        self.notify("Đã mở editor — quay lại màn check sau khi lưu.", timeout=4)

    @on(Button.Pressed, "#b_r")
    def _regen(self) -> None:
        self.app.push_screen(RegeneratePromptScreen(self._project_root))

    @on(Button.Pressed, "#b_b")
    def _back(self) -> None:
        ws.enqueue_monitor_command("context_back", {"project_root": self._project_root})
        log_system_action("monitor.cmd", "context_back")
        self.notify("Back đã gửi — quay CLI.", timeout=4)
        self.dismiss()

    @on(Button.Pressed, "#b_d")
    def _delete(self) -> None:
        ws.enqueue_monitor_command("context_delete", {"project_root": self._project_root})
        log_system_action("monitor.cmd", "context_delete")
        self.notify("Delete đã gửi — context sẽ xóa khi CLI drain.", timeout=5)
        self.dismiss()

    def action_dismiss(self) -> None:
        if hasattr(self.app, "_focus_cmd_input"):
            self.app._focus_cmd_input()  # type: ignore[attr-defined]
        self.dismiss()


class ConfirmExitScreen(ModalScreen[bool]):
    """Confirmation modal when user exits during an active workflow run."""

    BINDINGS = [Binding("escape", "cancel", "Cancel", show=False)]

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
                "[bold red]⚠ Workflow is running.[/bold red]\n\n"
                "[yellow]Exiting will delete all generated artifacts from this run:[/yellow]\n"
                "[dim]  • context.md and state.json will be removed\n"
                "  • Activity history and token records are preserved\n"
                "  • Pipeline state resets to idle[/dim]"
            )
            yield Horizontal(
                Button("Cancel — keep running", id="b_cancel", variant="primary"),
                Button("Exit & clean up", id="b_exit", variant="error"),
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

    BINDINGS = [Binding("escape", "cancel", "Skip", show=False)]

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
                "[bold yellow]● context.md deleted.[/bold yellow]\n"
                "[dim]Enter a new task to regenerate, or Esc to skip.[/dim]"
            )
            yield Input(id="del_input", placeholder="New task… (or Esc to skip)")

    def on_mount(self) -> None:
        try:
            self.query_one("#del_input", Input).focus()
        except LookupError:
            pass

    @on(Input.Submitted, "#del_input")
    def _submit(self, event: Input.Submitted) -> None:
        t = (event.value or "").strip()
        self.dismiss(t if t else None)

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
