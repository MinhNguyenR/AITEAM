"""Textual TUI: pipeline, activity log, notifications, context check, commands."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from textual.app import App, ComposeResult, on
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Input, RichLog, Static

from core.cli.context_flow import find_context_md, is_no_context
from core.cli.state import get_cli_settings, log_system_action
from core.cli.workflow.activity_log import format_activity_lines, list_recent_activity
from core.cli.workflow import session as ws
from core.cli.workflow.monitor_helpers import (
    _activity_min_ts_kw,
    _build_pipeline_markup,
    _checkpoint_blocks,
    _compute_visual_states,
    _display_name,
    _event_sequence_warning,
    _match_notification_id,
    _notifications_for_display,
    _project_root_default,
    _steps_for_tier,
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
        editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
        subprocess.run([editor, str(ctx)], check=False)
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


class WorkflowMonitorApp(App[None]):
    CSS = """
    Screen { background: #1a1b26; }
    #hint { background: #2b3049; color: #c8d3f5; padding: 0 1; height: auto; }
    #notif_area { background: #2f354a; color: #e0e8ff; padding: 1 2; height: auto; min-height: 6; border: solid #565f89; width: 100%; }
    #status_bar { background: #1f2335; color: #9aa5ce; padding: 0 2; height: 3; border: solid #3b4261; }
    #pipeline_static { background: #24283b; padding: 1 2; min-height: 8; text-style: bold; }
    #activity_log { height: 1fr; border: solid #3b4261; background: #16161e; }
    #cmd_input { dock: bottom; margin: 0 1; height: 3; border: solid #3b4261; }
    #main_split { height: 1fr; }
    #left_col { width: 34%; min-width: 26; }
    #right_col { width: 66%; min-width: 40; }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, view_mode: str | None = None) -> None:
        super().__init__()
        self._spin_idx = 0
        self._stream_shown_len = 0
        self._last_activity_ts = 0.0
        self._last_activity_line = ""
        self._view_mode = (view_mode or ws.get_workflow_last_view_mode() or "chain").lower()
        self._seen_activity_min_ts: float | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="hint")
        with Horizontal(id="main_split"):
            with Vertical(id="left_col"):
                yield Static("[bold]Activity / stream[/bold]", classes="panel-title")
                yield RichLog(id="activity_log", highlight=True, markup=True, wrap=True, auto_scroll=True)
            with Vertical(id="right_col"):
                yield Static(id="notif_area")
                yield Static(id="status_bar")
                yield Static(id="pipeline_static", expand=True)
        yield Input(
            id="cmd_input",
            placeholder="exit | log | check | dismiss <id> | view <id> | rewind gate | rewind node <name> | search <term>",
        )
        yield Footer()

    def action_quit(self) -> None:
        self.exit()

    def action_refresh(self) -> None:
        self._refresh_views()

    def on_mount(self) -> None:
        ws.apply_stale_workflow_ui_if_needed(_project_root_default())
        self.set_interval(0.25, self._tick_refresh)
        self._refresh_views()
        self._focus_cmd_input()

    def _focus_cmd_input(self) -> None:
        try:
            inp = self.query_one("#cmd_input", Input)
            inp.focus()
        except LookupError:
            pass

    def _bootstrap_activity_log(self) -> None:
        log = self.query_one("#activity_log", RichLog)
        log.clear()
        records = list_recent_activity(limit=80, min_ts=_activity_min_ts_kw())
        for line in format_activity_lines(records, ""):
            log.write(line)
        if records:
            self._last_activity_ts = max(float(r.get("ts") or 0.0) for r in records)

    def _tick_refresh(self) -> None:
        self._spin_idx += 1
        self._refresh_views()

    def _refresh_views(self) -> None:
        ws.prune_stale_pipeline_notifications()
        ws.apply_stale_workflow_ui_if_needed(_project_root_default())
        mt_kw = _activity_min_ts_kw() or 0.0
        if self._seen_activity_min_ts is None:
            self._seen_activity_min_ts = mt_kw
            self._bootstrap_activity_log()
        elif mt_kw > self._seen_activity_min_ts + 1e-9:
            self._seen_activity_min_ts = mt_kw
            act_log_reset = self.query_one("#activity_log", RichLog)
            act_log_reset.clear()
            self._bootstrap_activity_log()

        hint = self.query_one("#hint", Static)
        notif_el = self.query_one("#notif_area", Static)
        status = self.query_one("#status_bar", Static)
        pipe = self.query_one("#pipeline_static", Static)
        act_log = self.query_one("#activity_log", RichLog)

        tid = ws.get_thread_id()
        snap = ws.get_pipeline_snapshot()
        tier = snap["brief_tier"]
        last_node = ws.load_session().get("last_node")
        last_node_s = str(last_node) if last_node else None
        selected_leader = snap.get("brief_selected_leader") or ""
        stop_ph = snap.get("stop_phase") or "idle"
        now = time.time()
        st_msg = snap.get("status_message") or ""
        buf = snap.get("leader_stream_buffer") or ""

        if len(buf) < self._stream_shown_len:
            self._stream_shown_len = 0
        if len(buf) > self._stream_shown_len:
            self._stream_shown_len = len(buf)

        min_ts = self._last_activity_ts + 1e-9 if self._last_activity_ts > 0 else _activity_min_ts_kw()
        records = list_recent_activity(limit=120, min_ts=min_ts)
        if records:
            for line in format_activity_lines(records, ""):
                if line != self._last_activity_line:
                    act_log.write(line)
                    self._last_activity_line = line
            self._last_activity_ts = max(self._last_activity_ts, max(float(r.get("ts") or 0.0) for r in records))

        notifs = snap.get("notifications") or []
        shown = _notifications_for_display(notifs)
        if shown:
            lines: list[str] = []
            for n in shown:
                nid = str(n.get("id", ""))[:8]
                extra = n.get("extra") if isinstance(n.get("extra"), dict) else {}
                path = str(extra.get("state_path") or extra.get("context_path") or "")
                path_line = f"\n   [dim]{path}[/dim]" if path else ""
                lines.append(
                    f"{len(lines)+1}. [bold]{nid}[/bold] {n.get('title','')}{path_line}\n"
                    f"   [dim]dismiss {nid} | view {nid}[/dim]"
                )
            if any(str(x.get("kind")) == "state_json_ready" for x in shown):
                lines.append("[dim](Đóng hết state.json để xem thông báo context.md)[/dim]")
            notif_el.update("\n".join(lines))
        else:
            notif_el.update("[dim]Không có thông báo.[/dim]")

        status.update(
            f"[bold]Step[/bold] {snap.get('active_step')}  [bold]Tier[/bold] {tier or '—'}  "
            f"[bold]Pause[/bold] {'yes' if snap.get('paused_at_gate') else 'no'}  "
            f"[bold]Accept[/bold] {snap.get('context_accept_status') or 'none'}\n{st_msg}"
        )
        seq_warn = _event_sequence_warning()
        if seq_warn:
            status.update(
                f"[bold]Step[/bold] {snap.get('active_step')}  [bold]Tier[/bold] {tier or '—'}  "
                f"[bold]Pause[/bold] {'yes' if snap.get('paused_at_gate') else 'no'}  "
                f"[bold]Accept[/bold] {snap.get('context_accept_status') or 'none'}\n{st_msg}\n[yellow]{seq_warn}[/yellow]"
            )

        hint_lines = [
            f"[bold #7aa2f7]Workflow monitor ({self._view_mode})[/bold #7aa2f7]",
            f"Step {snap.get('active_step')}  Tier {tier or '—'}  Pause {'yes' if snap.get('paused_at_gate') else 'no'}",
        ]
        hint.update("\n".join(hint_lines))

        steps = _steps_for_tier(tier if tier else None)
        if not tier and snap["ambassador_status"] == "idle":
            steps = ["ambassador"]

        states = _compute_visual_states(steps, snap, last_node_s, now)
        if self._view_mode == "list":
            nodes = snap.get("workflow_list_nodes_state") or []
            rows: list[str] = []
            if not nodes:
                nodes = [{"node": sid, "status": states.get(sid, "pending"), "detail": ""} for sid in steps]
            for idx, n in enumerate(nodes, 1):
                node = str(n.get("node", ""))
                st = str(n.get("status", "pending")).lower()
                detail = str(n.get("detail", ""))[:180]
                badge = {
                    "pending": "[dim]PENDING[/dim]",
                    "running": "[yellow]RUNNING[/yellow]",
                    "complete": "[green]COMPLETE[/green]",
                    "error": "[red]ERROR[/red]",
                }.get(st, "[dim]PENDING[/dim]")
                rows.append(
                    f"[bold]{idx}. {_display_name(node)}[/bold]  {badge}\n"
                    f"┌──────────────────────────────────────────────┐\n"
                    f"│ {detail or ('Đang chờ chạy…' if st == 'pending' else 'Đang xử lý…')} \n"
                    f"└──────────────────────────────────────────────┘"
                )
            pipe.update("\n\n".join(rows))
        else:
            markup = _build_pipeline_markup(steps, states, tier, selected_leader, self._spin_idx)
            pipe.update(markup)

    @on(Input.Submitted, "#cmd_input")
    def _on_cmd(self, event: Input.Submitted) -> None:
        raw = (event.value or "").strip()
        event.input.value = ""
        if not raw:
            return
        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""
        root = _project_root_default()

        log_system_action("monitor.input", raw[:300])

        if cmd == "exit":
            self.exit()
            return

        if cmd == "log":
            self.push_screen(ActivityLogScreen())
            self.set_timer(0.05, self._focus_cmd_input)
            return

        if cmd == "check":
            self.push_screen(ContextReviewScreen(root))
            self.set_timer(0.05, self._focus_cmd_input)
            return

        if cmd == "dismiss":
            if not rest:
                self.notify("Cần id: dismiss <id>", severity="warning")
                return
            nid = _match_notification_id(rest) or rest
            ws.dismiss_pipeline_notification(nid)
            self.notify(f"Đã dismiss {nid[:8]}…")
            return

        if cmd == "view":
            if not rest:
                self.notify("view <id thông báo>", severity="warning")
                return
            nid = _match_notification_id(rest)
            if not nid:
                self.notify("Không tìm thấy thông báo.", severity="warning")
                return
            for n in ws.list_active_notifications():
                if str(n.get("id")) == nid:
                    ex = n.get("extra") if isinstance(n.get("extra"), dict) else {}
                    path = ex.get("context_path") or ex.get("state_path")
                    if path:
                        self.push_screen(ContextFilePreviewScreen(str(path)))
                    else:
                        self.notify("Thông báo không có đường dẫn file.", severity="warning")
                    return
            return

        if cmd == "rewind":
            if not rest:
                self.notify("Dùng: rewind gate | rewind node <name>", severity="warning")
                return
            if rest.lower() == "gate":
                ws.enqueue_monitor_command("rewind_gate", {})
                self.notify("rewind gate đã gửi.", timeout=4)
                return
            if rest.lower().startswith("node "):
                node = rest[5:].strip()
                if not node:
                    self.notify("rewind node <name>", severity="warning")
                    return
                ws.enqueue_monitor_command("rewind_checkpoint", {"target": node})
                self.notify("rewind node đã gửi.", timeout=4)
                return
            self.notify("Dùng: rewind gate | rewind node <name>", severity="warning")
            return

        if cmd == "search":
            self.push_screen(CheckpointSearchScreen(rest))
            self.set_timer(0.05, self._focus_cmd_input)
            return

        self.notify(f"Lệnh không hỗ trợ: {cmd}", severity="error")
        self._focus_cmd_input()


def main() -> None:
    mode: str | None = None
    argv = list(sys.argv[1:])
    if "--view" in argv:
        idx = argv.index("--view")
        if idx + 1 < len(argv):
            mode = argv[idx + 1]
    if not mode:
        mode = os.environ.get("WORKFLOW_VIEW_MODE")
    if not mode:
        mode = ws.get_workflow_last_view_mode()
    if not mode:
        mode = str(get_cli_settings().get("workflow_view_mode") or "chain")
    mode = "list" if str(mode).lower() == "list" else "chain"
    ws.set_workflow_last_view_mode(mode)
    WorkflowMonitorApp(view_mode=mode).run()


if __name__ == "__main__":
    main()
