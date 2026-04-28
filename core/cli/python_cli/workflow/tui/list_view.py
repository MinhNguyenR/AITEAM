"""Workflow LIST monitor — prompt_toolkit, no Textual, no borders.

Layout:
  hint bar  (1 line, top)
  ─────────────────────────────────────────────────────
  content   (fills remaining — history + live step)
    scrollable with arrow keys / page up/down
  ─────────────────────────────────────────────────────
  hints bar (1 line)
  ▸ input   (1 line, bottom, no border)

Design rules:
  - NO borders anywhere — same bg as terminal (#000000)
  - Scrolling: Up/PageUp scrolls history; End/Ctrl-End snaps to bottom
  - check command: opens full-screen overlay with context.md + accept/delete
  - gate state NEVER reset by timer (only by user action)
  - Regenerate: spinner while regenerating, green on accept, red on decline
"""

from __future__ import annotations

import asyncio
import queue
import threading
import time
from io import StringIO
from typing import Optional

from rich.console import Console as RichConsole
from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import (
    ConditionalContainer, FloatContainer, Float, HSplit, Window,
)
from prompt_toolkit.layout.controls import (
    BufferControl, FormattedTextControl, UIContent, UIControl,
)
from prompt_toolkit.layout.dimension import Dimension as D
from prompt_toolkit.layout.processors import BeforeInput
from prompt_toolkit.data_structures import Point
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI, to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.styles import Style
from prompt_toolkit.output.color_depth import ColorDepth

from ..runtime import session as ws
from .monitor_helpers import (
    TOKEN_WARN_THRESHOLD,
    _activity_min_ts_kw,
    _match_notification_id,
    _parse_file_events,
    _parse_token_counts,
    _parse_token_counts_for_node,
    _project_root_default,
)

_GEN_STEPS = frozenset({"ambassador", "leader_generate", "expert_solo", "expert_coplan"})
_SPINNER   = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

_ROLE: dict[str, str] = {
    "ambassador":         "Ambassador",
    "leader_generate":    "Leader",
    "expert_solo":        "Expert",
    "expert_coplan":      "Expert",
    "human_context_gate": "Human Gate",
    "finalize_phase1":    "Finalize",
}
_ACTION: dict[str, str] = {
    "ambassador":         "Generate state.json",
    "leader_generate":    "Generate context.md",
    "expert_solo":        "Generate context.md",
    "expert_coplan":      "Generate context.md",
    "human_context_gate": "Review context.md",
    "finalize_phase1":    "Finalize pipeline",
}

_CMD_HINT = "/ask <q>  ·  /agent <task>  ·  check  ·  log  ·  info  ·  btw <note>  ·  exit"

_GATE_WAITING  = "waiting"
_GATE_ACCEPTED = "accepted"
_GATE_DECLINED = "declined"
_GATE_REGEN    = "regen"


_WORKFLOW_ASK_SYSTEM = """Bạn là AI assistant tích hợp trong workflow tool aiteam.
Bạn trả lời câu hỏi, giải thích khái niệm, hỗ trợ code.

QUAN TRỌNG — Khi user muốn viết code, build software, implement gì đó:
- Khuyên dùng AGENT MODE: /agent <mô tả task>
- Ví dụ: /agent viết RAG pipeline với FAISS và FastAPI

Các lệnh trong workflow:
  /agent <task>  — Khởi chạy AI agent pipeline (Ambassador → Leader → Review → Finalize)
  /ask <câu hỏi> — Hỏi AI (mode hiện tại)
  /btw <ghi chú> — Gửi ghi chú cho agent đang chạy (chỉ khi pipeline active)
  check          — Xem context.md đã generate trước khi accept/decline
  accept         — Chấp nhận context.md, pipeline tiếp tục
  delete         — Từ chối, có thể regenerate
  log            — Xem activity log
  info           — Xem thông tin pipeline (role, model, token)
  exit           — Thoát workflow

Pipeline flow: Ambassador phân tích → Leader/Expert tạo context.md → Human review → Finalize
Tier: LOW/MEDIUM/HARD/EXPERT xác định độ phức tạp và model được dùng.
"""

# ── ANSI conversion ───────────────────────────────────────────────────────────

def _r2a(markup: str, width: int = 160) -> str:
    """Rich markup → ANSI escape codes."""
    if markup == "":
        return ""
    sio = StringIO()
    con = RichConsole(file=sio, highlight=False, markup=True,
                      width=width, force_terminal=True, no_color=False)
    con.print(markup, end="")
    return sio.getvalue()


# ── Scrollable history UIControl ──────────────────────────────────────────────

class _HistoryControl(UIControl):
    """Colored, scrollable content area.

    scroll_offset=0  → cursor at last line (auto-follow)
    scroll_offset>0  → user scrolled up (cursor above last line)
    """

    def __init__(self, app: "WorkflowListApp") -> None:
        self._app = app

    def create_content(self, width: int, height: int) -> UIContent:
        lines = self._app._get_all_lines()
        display: list[list] = []
        for ansi_str in lines:
            for part in ansi_str.rstrip("\n").split("\n"):
                display.append(to_formatted_text(ANSI(part)))
        n = len(display)
        offset = self._app._scroll_offset
        cursor_y = max(0, n - 1 - offset) if n > 0 else 0
        _d = display  # capture for closure safety

        def get_line(i: int) -> list:
            return _d[i] if 0 <= i < len(_d) else []

        return UIContent(
            get_line=get_line,
            line_count=max(1, n),
            cursor_position=Point(x=0, y=cursor_y),
        )

    def is_focusable(self) -> bool:
        return False

    def mouse_handler(self, mouse_event: MouseEvent):
        n = len(self._app._get_all_lines())
        if mouse_event.event_type == MouseEventType.SCROLL_UP:
            self._app._scroll_offset = min(self._app._scroll_offset + 3, max(0, n - 1))
            if self._app._app: self._app._app.invalidate()
            return None
        elif mouse_event.event_type == MouseEventType.SCROLL_DOWN:
            self._app._scroll_offset = max(0, self._app._scroll_offset - 3)
            if self._app._app: self._app._app.invalidate()
            return None
        return NotImplemented


# ── Check-view UIControl ──────────────────────────────────────────────────────

class _CheckControl(UIControl):
    """Full-screen context.md viewer content."""

    def __init__(self, app: "WorkflowListApp") -> None:
        self._app = app

    def create_content(self, width: int, height: int) -> UIContent:
        lines_raw = self._app._check_lines
        display: list[list] = []
        for raw in lines_raw:
            for part in raw.rstrip("\n").split("\n"):
                display.append(to_formatted_text(ANSI(part)))
        n = len(display)
        offset = self._app._check_scroll
        cursor_y = max(0, n - 1 - offset) if n > 0 else 0
        _d = display

        def get_line(i: int) -> list:
            return _d[i] if 0 <= i < len(_d) else []

        return UIContent(
            get_line=get_line,
            line_count=max(1, n),
            cursor_position=Point(x=0, y=cursor_y),
        )

    def is_focusable(self) -> bool:
        return False


# ── App ───────────────────────────────────────────────────────────────────────


def _get_role_display(step_id: str) -> str:
    """Get actual configured role name (e.g. Leader_Medium, Expert)."""
    snap = ws.get_pipeline_snapshot()
    tier = snap.get("brief_tier")
    try:
        from .monitor_helpers import _registry_key_for_step
        from core.config import config as _cfg
        key = _registry_key_for_step(step_id, tier)
        if key:
            cfg = _cfg.get_worker(key) or {}
            role = str(cfg.get("role", "") or "")
            if role:
                return role
    except Exception:
        pass
    # fallback to generic names
    return {
        "ambassador":         "Ambassador",
        "leader_generate":    "Leader",
        "expert_solo":        "Expert",
        "expert_coplan":      "Expert",
        "human_context_gate": "Human Gate",
        "finalize_phase1":    "Finalize",
    }.get(step_id, step_id)

class WorkflowListApp:

    def __init__(self) -> None:
        self._history_raw:  list[str]       = []
        self._live_raw:     str             = ""
        self._hint_raw:     str             = ""
        self._spin:         int             = 0
        self._scroll_offset: int           = 0  # 0=bottom, >0=scrolled up

        # Pipeline state
        self._seen_activity_min_ts: Optional[float] = None
        self._last_active_step:     str             = ""
        self._shown_file_events:    list            = []
        self._token_warned:         bool            = False
        self._seen_running:         bool            = False
        self._pipeline_pending:     bool            = False

        # Inline modes
        self._post_delete_mode:  bool           = False
        self._exit_confirm_mode: bool           = False
        self._task_mode_pending: Optional[str]  = None
        self._last_task_text:    str            = ""
        self._attempt_count:     int            = 1
        self._gate_state:        str            = _GATE_WAITING

        # Check-view state
        self._check_mode:   bool        = False
        self._check_lines:  list[str]   = []
        self._check_scroll: int         = 0
        self._check_ctx_path: str       = ""
        self._check_auto_refresh: bool  = False
        self._ask_thinking:       bool  = False  # True while /ask is getting response
        self._clarif_mode:        bool  = False  # True while clarification is pending
        self._clarif_data:        dict  = {}     # {question, options}

        self._cmd_q: queue.Queue       = queue.Queue()
        self._app:   Optional[Application] = None
        self._main_buffer: Optional[Buffer] = None
        self._check_buffer: Optional[Buffer] = None

    # ── content helpers ───────────────────────────────────────────────────────

    def _write(self, markup: str, indent: bool = False) -> None:
        display = markup
        self._history_raw.append(_r2a(display))
        try:
            ws.append_stream_line(display)
        except Exception:
            pass
        if self._app:
            self._app.invalidate()

    def _set_live(self, markup: str) -> None:
        """Set live step content. Converts each markup line separately to avoid
        ANSI code bleeding when the string is later split by newline."""
        if not markup:
            self._live_raw = ""
            return
        # Convert each line separately so ANSI codes are self-contained per line
        lines = markup.split("\n")
        ansi_lines = [_r2a(line) for line in lines]
        self._live_raw = "\n".join(ansi_lines)

    def _get_all_lines(self) -> list[str]:
        lines = list(self._history_raw)
        if self._live_raw:
            lines.append(self._live_raw)
        return lines

    def _replay_history(self) -> None:
        try:
            for markup in ws.get_stream_history():
                self._history_raw.append(_r2a(markup))
        except Exception:
            pass

    # ── layout ────────────────────────────────────────────────────────────────

    def _build_app(self) -> Application:
        # Hint bar
        def _hint_text():
            return to_formatted_text(ANSI(self._hint_raw or ""))

        hint_win = Window(
            content=FormattedTextControl(_hint_text, focusable=False),
            height=1,
        )

        # Main content (history + live)
        content_win = Window(
            content=_HistoryControl(self),
            dont_extend_height=False,
        )

        # Hints bar
        _hints_ansi = _r2a(f"[dim]{_CMD_HINT}[/dim]")

        def _hints_text():
            return to_formatted_text(ANSI(_hints_ansi))

        hints_win = Window(
            content=FormattedTextControl(_hints_text, focusable=False),
            height=1,
        )

        # Command input — Buffer + BufferControl, no border, no styling
        self._main_buffer = Buffer(
            multiline=False,
            accept_handler=lambda buff: self._cmd_q.put(buff.text),
        )
        input_win = Window(
            content=BufferControl(
                buffer=self._main_buffer,
                input_processors=[BeforeInput("▸ ")],
                focusable=True,
            ),
            height=1,
        )

        # Check-view content
        def _check_hint_text():
            ctx = self._check_ctx_path
            return to_formatted_text(ANSI(
                _r2a(f"[bold]context.md[/bold]  [dim]{ctx}[/dim]"
                     f"  [bold yellow]— accept · delete · close[/bold yellow]")
            ))

        check_hint_win = Window(
            content=FormattedTextControl(_check_hint_text, focusable=False),
            height=1,
        )
        check_content_win = Window(content=_CheckControl(self))

        _check_hints_ansi = _r2a(
            "[dim]accept — accept context  ·  delete — reject context  ·  q/Esc — close[/dim]"
        )

        check_hints_win = Window(
            content=FormattedTextControl(
                lambda: to_formatted_text(ANSI(_check_hints_ansi)),
                focusable=False,
            ),
            height=1,
        )
        self._check_buffer = Buffer(
            multiline=False,
            accept_handler=lambda buff: self._cmd_q.put("__check__:" + buff.text),
        )
        check_input_win = Window(
            content=BufferControl(
                buffer=self._check_buffer,
                input_processors=[BeforeInput("▸ ")],
                focusable=True,
            ),
            height=1,
        )

        @Condition
        def _in_check():
            return self._check_mode

        @Condition
        def _in_workflow():
            return not self._check_mode

        # Separator with "aiteam" label above input
        _sep_ansi = _r2a("[dim]──── [bold]aiteam[/bold] ─────────────────────────────────────────────[/dim]")
        sep_win = Window(
            content=FormattedTextControl(
                lambda: to_formatted_text(ANSI(_sep_ansi)), focusable=False
            ),
            height=1,
        )
        main_layout = ConditionalContainer(
            content=HSplit([hint_win, content_win, hints_win, sep_win, input_win]),
            filter=_in_workflow,
        )
        check_layout = ConditionalContainer(
            content=HSplit([check_hint_win, check_content_win, check_hints_win, check_input_win]),
            filter=_in_check,
        )

        layout = Layout(
            HSplit([main_layout, check_layout]),
            focused_element=self._main_buffer,
        )

        # Key bindings
        kb = KeyBindings()

        @kb.add("c-c", eager=True)
        def _ctrl_c(event):
            if self._check_mode:
                self._close_check()
                return
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", ""):
                self._ask_exit_inline()
            else:
                event.app.exit()

        @kb.add("c-up", eager=True)
        @kb.add("up", eager=True)
        def _scroll_up(event):
            n = len(self._get_all_lines())
            self._scroll_offset = min(self._scroll_offset + 3, max(0, n - 1))
            event.app.invalidate()

        @kb.add("c-down", eager=True)
        @kb.add("down", eager=True)
        def _scroll_down(event):
            self._scroll_offset = max(0, self._scroll_offset - 3)
            event.app.invalidate()

        @kb.add("c-end", eager=True)
        def _snap_bottom(event):
            self._scroll_offset = 0
            event.app.invalidate()

        @kb.add("pageup", eager=True)
        def _page_up(event):
            n = len(self._get_all_lines())
            self._scroll_offset = min(self._scroll_offset + 10, max(0, n - 1))
            event.app.invalidate()

        @kb.add("pagedown", eager=True)
        def _page_down(event):
            self._scroll_offset = max(0, self._scroll_offset - 10)
            event.app.invalidate()

        # Mouse scroll wheel
        try:
            @kb.add("<scroll-up>", eager=True)
            def _mouse_up(event):
                n = len(self._get_all_lines())
                self._scroll_offset = min(self._scroll_offset + 3, max(0, n - 1))
                event.app.invalidate()

            @kb.add("<scroll-down>", eager=True)
            def _mouse_down(event):
                self._scroll_offset = max(0, self._scroll_offset - 3)
                event.app.invalidate()
        except Exception:
            pass

        @kb.add("c-up", eager=True, filter=_in_check)
        def _check_up(event):
            n = len(self._check_lines)
            self._check_scroll = min(self._check_scroll + 1, max(0, n - 1))
            event.app.invalidate()

        @kb.add("c-down", eager=True, filter=_in_check)
        def _check_down(event):
            self._check_scroll = max(0, self._check_scroll - 1)
            event.app.invalidate()

        @kb.add("escape", filter=_in_check)
        @kb.add("c-c", filter=_in_check, eager=True)
        def _check_close(event):
            self._close_check()

        style = Style([])

        return Application(
            layout=layout,
            key_bindings=kb,
            full_screen=True,
            color_depth=ColorDepth.TRUE_COLOR,
            style=style,
            mouse_support=True,   # mouse wheel scroll
            enable_page_navigation_bindings=False,
        )

    # ── check view ────────────────────────────────────────────────────────────

    def _open_check(self, root: str) -> None:
        try:
            from core.cli.python_cli.flows.context_flow import find_context_md, is_no_context
            ctx = find_context_md(root)
            if not ctx or is_no_context(ctx):
                self._write(f"[dim]✗ No context.md found[/dim]")
                return
            lines_raw: list[str] = []
            lines_raw.append(_r2a(f"[bold]── context.md ──────────────────────────────────[/bold]"))
            for line in ctx.read_text(encoding="utf-8").splitlines():
                # Escape Rich markup in context content
                safe = line.replace("[", r"\[")
                lines_raw.append(_r2a(f"[dim]{safe}[/dim]"))
            lines_raw.append(_r2a(f"[dim]─────────────────────────────────────────────────[/dim]"))
            lines_raw.append(_r2a(
                f"[bold yellow]accept[/bold yellow] accept  ·  "
                f"[bold red]delete[/bold red] reject  ·  "
                f"[dim cyan]edit[/dim cyan] open editor  ·  "
                f"[dim]q/Esc close[/dim]"
            ))
            self._check_lines   = lines_raw
            self._check_scroll  = 0
            self._check_ctx_path = str(ctx)
            self._check_mode    = True
            if self._app:
                self._app.layout.focus(self._check_buffer)
                self._app.invalidate()
        except Exception as e:
            self._write(f"[red]✗ check error: {e}[/red]")

    def _close_check(self) -> None:
        self._check_mode  = False
        self._check_lines = []
        if self._app:
            self._app.layout.focus(self._main_buffer)
            self._app.invalidate()

    def _handle_check_cmd(self, cmd: str) -> None:
        root = _project_root_default()
        c = cmd.strip().lower()

        if c == "edit":
            # Open editor WITHOUT closing check view
            # The tick loop will refresh the check content automatically
            try:
                from core.cli.python_cli.flows.context_flow import find_context_md
                from core.cli.python_cli.safe_editor import build_editor_argv
                import subprocess
                ctx = find_context_md(root)
                if not ctx:
                    self._check_lines = [_r2a("[dim]✗ No context.md found[/dim]")]
                    if self._app: self._app.invalidate()
                    return
                subprocess.Popen(build_editor_argv(ctx))
                # Start auto-refresh of check content while editor is open
                self._check_auto_refresh = True
            except Exception as e:
                self._check_lines = [_r2a(f"[red]✗ edit error: {e}[/red]")]
                if self._app: self._app.invalidate()
            return

        if c in ("accept",):
            self._close_check()
            self._write(f"[bold green]●[/bold green] [bold]Human Gate[/bold]")
            self._write(f"[dim]└──[/dim] [green]Accepting context.md…[/green]  [bold green]●[/bold green]")
            self._gate_state = _GATE_ACCEPTED

            def _accept_bg():
                try:
                    from core.cli.python_cli.flows.context.monitor_actions import apply_context_accept_from_monitor
                    apply_context_accept_from_monitor(root)
                except Exception:
                    pass
            threading.Thread(target=_accept_bg, daemon=True).start()

        elif c in ("delete",):
            self._close_check()
            try:
                from core.cli.python_cli.flows.context.monitor_actions import apply_context_delete_from_monitor
                apply_context_delete_from_monitor(root)
                self._gate_state       = _GATE_DECLINED
                self._post_delete_mode = True
                self._write(f"[red]✗[/red] [bold]Human Gate[/bold]")
                self._write(f"[dim]└──[/dim] [red]context.md deleted — Rejected[/red]")
                self._write(
                    f"[dim]    Regenerate [bold]'{self._last_task_text[:50]}'[/bold]? (y/n)[/dim]"
                    if self._last_task_text
                    else f"[dim]    Regenerate? (y/n)[/dim]"
                )
            except Exception as e:
                self._write(f"[red]✗ Delete failed: {e}[/red]")

        elif c in ("q", "quit", "close", "back", ""):
            self._close_check()

        else:
            pass  # ignore other input in check mode

    # ── async tick ────────────────────────────────────────────────────────────

    async def _tick_loop(self) -> None:
        while True:
            await asyncio.sleep(0.25)
            self._spin += 1
            # Auto-refresh check content if editor is open
            if self._check_mode and self._check_auto_refresh:
                try:
                    from core.cli.python_cli.flows.context_flow import find_context_md
                    ctx = find_context_md(_project_root_default())
                    if ctx and ctx.exists():
                        lines_raw = [_r2a(f"[bold]── context.md ──[/bold]  [dim]{ctx}[/dim]")]
                        for line in ctx.read_text(encoding="utf-8").splitlines():
                            safe = line.replace("[", r"\[")
                            lines_raw.append(_r2a(f"[dim]{safe}[/dim]"))
                        lines_raw.append(_r2a("[dim]accept  ·  delete  ·  edit  ·  q close[/dim]"))
                        self._check_lines = lines_raw
                except Exception:
                    pass

            # Drain command queue
            while not self._cmd_q.empty():
                try:
                    raw = self._cmd_q.get_nowait()
                    if raw.startswith("__check__:"):
                        self._handle_check_cmd(raw[10:])
                    else:
                        self._handle_cmd(raw)
                except queue.Empty:
                    break
            # Auto-exit when pipeline finishes
            snap   = ws.get_pipeline_snapshot()
            active = str(snap.get("active_step") or "idle")
            if active not in ("idle", "end_failed", "") or snap.get("ambassador_status") == "running":
                self._seen_running = True
                self._pipeline_pending = False
            if ((self._seen_running or self._pipeline_pending) and snap.get("run_finished")
                    and not snap.get("paused_at_gate")
                    and self._gate_state == _GATE_WAITING):
                if snap.get("graph_failed"):
                    self._write("")
                    self._write(f"[bold red]✗[/bold red] [bold]Pipeline thất bại[/bold] — {time.strftime('%H:%M:%S')}")
                    self._write(f"[dim]  Dùng log  ·  /agent <task> thử lại  ·  exit để thoát[/dim]")
                    self._set_live("")
                    self._scroll_offset = 0
                else:
                    self._flush_final(snap)
                self._seen_running    = False
                self._pipeline_pending = False
                try:
                    ws.set_pipeline_run_finished(False)
                    ws.reset_pipeline_visual()
                except Exception:
                    pass
            self._refresh()
            if self._app:
                self._app.invalidate()

    # ── render ────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        ws.prune_stale_pipeline_notifications()
        ws.apply_stale_workflow_ui_if_needed(_project_root_default())

        snap   = ws.get_pipeline_snapshot()
        tier   = snap.get("brief_tier")
        toast  = str(snap.get("toast") or "")
        buf    = str(snap.get("leader_stream_buffer") or "")
        active = str(snap.get("active_step") or "idle")

        # Activity min_ts reset — NEVER reset _gate_state here
        mt = _activity_min_ts_kw() or 0.0
        if self._seen_activity_min_ts is None:
            self._seen_activity_min_ts = mt
        elif mt > self._seen_activity_min_ts + 1e-9:
            self._seen_activity_min_ts = mt
            self._last_active_step  = ""
            self._shown_file_events = []
            self._token_warned      = False

        pt, ct = _parse_token_counts()
        if (pt + ct) > TOKEN_WARN_THRESHOLD and not self._token_warned:
            self._token_warned = True
            self._write(f"[bold yellow]⚠ Token budget: {pt+ct:,} / 262k[/bold yellow]")

        # Hint bar (raw ANSI — no Rich overhead)
        sc  = _SPINNER[self._spin % len(_SPINNER)]
        tok = f"  in:{pt:,} out:{ct:,}" if (pt or ct) else ""
        running = active not in ("idle", "end_failed", "")
        adisp = f"\x1b[90m{sc}\x1b[0m \x1b[33m{active}\x1b[0m" if running else f"\x1b[2m{active}\x1b[0m"
        tp    = f"\x1b[33m{toast}\x1b[0m  " if toast.strip() else ""
        self._hint_raw = (
            f"{tp}\x1b[34mlist\x1b[0m  {adisp}  Tier {tier or '—'}"
            + (f"\x1b[2m{tok}\x1b[0m" if tok else "")
        )

        # ── Clarification gate check ──────────────────────────────────────────
        clarif = None
        try:
            clarif = ws.get_clarification() if hasattr(ws, "get_clarification") else None
        except Exception:
            pass
        if clarif and clarif.get("pending"):
            self._clarif_mode = True
            self._clarif_data = clarif
            self._render_clarification(clarif)
            return  # Skip normal rendering while clarification is pending
        elif self._clarif_mode and not (clarif and clarif.get("pending")):
            # Clarification just resolved — clear mode
            self._clarif_mode = False
            self._clarif_data = {}
            self._set_live("")
        # ──────────────────────────────────────────────────────────────────────

        # Step transitions
        if active != self._last_active_step:
            self._on_step_transition(self._last_active_step, active)
            self._last_active_step = active

        # Per-role tokens: use node-specific event if available
        # Otherwise estimate from buffer size (chars/4 ≈ tokens)
        node_pt, node_ct = (_parse_token_counts_for_node(active)
                            if active in _GEN_STEPS else (0, 0))
        if active in _GEN_STEPS and not (node_pt or node_ct):
            # Estimate completion tokens from buffer length while model streams
            est_ct = len(buf) // 4 if buf else 0
            node_ct = est_ct  # no global fallback — avoid showing wrong role's tokens

        self._render_live(active, buf, node_pt, node_ct)

        # File events — track silently (don't show long paths)
        file_evs = _parse_file_events()
        if file_evs:
            self._shown_file_events = file_evs

    def _on_step_transition(self, prev: str, active: str) -> None:
        pt, ct = _parse_token_counts_for_node(prev) if prev in _GEN_STEPS else (0, 0)

        if prev in _GEN_STEPS:
            role   = _get_role_display(prev)
            action = _ACTION.get(prev, prev)
            tok    = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
            self._write("")
            self._write(f"[bold green]●[/bold green] [bold]{role}[/bold]")
            self._write(f"[dim]└──[/dim] {action}  [bold green]●[/bold green]{tok}")
            # If transitioning to gate: add context.md done message + hint
            if active == "human_context_gate":
                self._write(f"[dim]    └──[/dim] [green]context.md đã xong[/green]  [bold green]●[/bold green]")
                self._write(f"[dim]            nhập [bold]check[/bold] để xem  ·  accept  ·  decline  ·  edit[/dim]")

        elif prev == "human_context_gate" and active not in ("human_context_gate",):
            if self._gate_state == _GATE_ACCEPTED:
                self._write("")
                self._write(f"[bold green]●[/bold green] [bold]Human Gate[/bold]")
                self._write(f"[dim]└──[/dim] [green]Đã đồng ý[/green]  [bold green]✓[/bold green]")

        if active in _GEN_STEPS or active in ("human_context_gate", "finalize_phase1"):
            self._write("")

        if active == "human_context_gate" and prev != "human_context_gate":
            # context.md ready branch already written in leader completion above
            self._scroll_offset = 0

    def _render_live(self, active: str, buf: str, pt: int, ct: int) -> None:
        sc = _SPINNER[self._spin % len(_SPINNER)]

        # Gate state shown regardless of active (reset_pipeline_visual sets active→idle)
        if self._gate_state == _GATE_DECLINED:
            task_hint = f" [bold]'{self._last_task_text[:40]}'[/bold]" if self._last_task_text else ""
            self._set_live(
                f"[red]●[/red] [bold]Human Gate[/bold]\n"
                f"[dim]└──[/dim] [red]Đã từ chối[/red]\n"
                f"[dim]   └──[/dim] [#888888]{sc}[/#888888] Regenerate{task_hint}? [bold yellow](y/n)[/bold yellow]"
            )
            return

        if self._gate_state == _GATE_REGEN:
            task_hint = f" [bold]'{self._last_task_text[:40]}'[/bold]" if self._last_task_text else ""
            self._set_live(
                f"[red]●[/red] [bold]Human Gate[/bold]\n"
                f"[dim]└──[/dim] [red]Đã từ chối[/red]\n"
                f"[dim]   └──[/dim] [bold green]●[/bold green] [green]Đã chọn regenerate[/green]{task_hint}"
            )
            return

        if active in ("idle", "", "end_failed"):
            self._set_live("")
            return

        if active in _GEN_STEPS:
            role   = _get_role_display(active)
            action = _ACTION.get(active, active)
            meta: list[str] = []
            if pt or ct:
                meta.append(f"token in: {pt:,}  token out: {ct:,}")
            if self._attempt_count > 1:
                meta.append(f"attempts: {self._attempt_count}")
            meta_s = f"  [dim]({', '.join(meta)})[/dim]" if meta else ""

            buf_lines = [ln for ln in buf.split("\n") if ln.strip()] if buf else []
            last6     = buf_lines[-6:]
            parts     = [
                f"[#888888]{sc}[/#888888] [bold]{role}[/bold]",
                f"[dim]└──[/dim] {action}{meta_s}",
            ]
            if last6:
                parts.append(f"[dim]    └── {last6[0][:98]}[/dim]")
                for ln in last6[1:]:
                    parts.append(f"[dim]        {ln[:98]}[/dim]")
            self._set_live("\n".join(parts))

        elif active == "human_context_gate":
            if self._gate_state == _GATE_ACCEPTED:
                self._set_live(
                    f"[bold green]●[/bold green] [bold]Human Gate[/bold]\n"
                    f"[dim]└──[/dim] [green]Đã đồng ý[/green]  [bold green]✓[/bold green]"
                )
            else:  # GATE_WAITING
                self._set_live(
                    f"[#888888]{sc}[/#888888] [bold]Human Gate[/bold]\n"
                    f"[dim]└──[/dim] Review context.md"
                    f"  [dim](check · accept · delete)[/dim]"
                )

        elif active == "finalize_phase1":
            self._set_live(f"[dim]{sc}[/dim] [bold]Finalize[/bold]\n[dim]└── Finalizing…[/dim]")

        else:
            self._set_live(f"[dim]{sc} {active}[/dim]")

    def _flush_final(self, snap: dict) -> None:
        pt, ct   = _parse_token_counts()
        tok      = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
        file_evs = _parse_file_events()
        self._shown_file_events = file_evs  # silently consume
        self._write("")
        self._write(f"[bold green]●[/bold green] [bold]Pipeline complete[/bold] — {time.strftime('%H:%M:%S')}{tok}")
        self._set_live("")
        self._scroll_offset = 0

    # ── countdown ────────────────────────────────────────────────────────────

    def _start_decline_countdown(self) -> None:
        self._write(f"[dim]  Clearing in 3…[/dim]")

        def _run() -> None:
            for r in (2, 1, 0):
                time.sleep(1.0)
                def _upd(r=r):
                    self._write(f"[dim]  Clearing in {r}…[/dim]")
                    if self._app: self._app.invalidate()
                if self._app:
                    self._app.loop.call_soon_threadsafe(_upd)
                else:
                    _upd()

            def _clear():
                self._history_raw.clear()
                self._set_live("")
                self._scroll_offset     = 0
                self._last_active_step  = ""
                self._shown_file_events = []
                self._gate_state        = _GATE_WAITING
                self._seen_running      = False
                self._pipeline_pending  = False
                try:
                    ws.clear_stream_history()
                except Exception:
                    pass
                ws.reset_pipeline_visual()
                if self._app: self._app.invalidate()

            if self._app:
                self._app.loop.call_soon_threadsafe(_clear)
            else:
                _clear()

        threading.Thread(target=_run, daemon=True).start()

    # ── inline helpers ────────────────────────────────────────────────────────

    def _ask_exit_inline(self) -> None:
        self._exit_confirm_mode = True
        self._write("")
        self._write(f"[bold yellow]⚠[/bold yellow] Workflow running — Exit & cleanup? [bold](y/n)[/bold]")
        self._scroll_offset = 0

    def _do_cleanup_exit(self) -> None:
        self._write(f"[dim]  Stopping pipeline…[/dim]")
        try:
            ws.request_pipeline_stop()
        except Exception:
            pass
        try:
            from core.cli.python_cli.flows.context.monitor_actions import apply_context_delete_from_monitor
            apply_context_delete_from_monitor(_project_root_default())
        except Exception:
            pass
        ws.reset_pipeline_visual()
        if self._app:
            self._app.exit()

    def _handle_ask_inline(self, question: str) -> None:
        self._write("")
        self._write(f"[bold #7aa2f7]User[/bold #7aa2f7]")
        self._write(f"[dim]----------------[/dim]")
        self._write(f"[bold #7aa2f7]>>[/bold #7aa2f7] {question}")
        self._ask_thinking = True
        self._set_live(f"[dim]   [#888888]{_SPINNER[self._spin % len(_SPINNER)]}[/#888888] thinking…[/dim]")
        self._scroll_offset = 0

        def _run() -> None:
            try:
                from core.cli.python_cli.flows.ask_model_selector import _ask_model
                from agents.chat_agent import CHAT_WORKFLOW_SYSTEM_PROMPT
                msgs  = [{"role": "system", "content": CHAT_WORKFLOW_SYSTEM_PROMPT}]
                msgs.append({"role": "user", "content": question})
                reply = _ask_model("standard", msgs)
                words, curr, chunks = reply.split(), "", []
                for w in words:
                    if len(curr) + len(w) + 1 > 100:
                        chunks.append(curr); curr = w
                    else:
                        curr = (curr + " " + w).strip()
                if curr:
                    chunks.append(curr)

                def _show():
                    self._ask_thinking = False
                    self._set_live("")
                    self._write("")
                    self._write(f"[bold #9ece6a]Assistant[/bold #9ece6a]")
                    self._write(f"[dim]----------------[/dim]")
                    for chunk in chunks:
                        self._write(f"[#9ece6a]>>[/#9ece6a] {chunk}")
                    self._scroll_offset = 0
                    if self._app: self._app.invalidate()

                if self._app:
                    self._app.loop.call_soon_threadsafe(_show)
                else:
                    _show()
            except Exception as e:
                def _err():
                    self._ask_thinking = False
                    self._write(f"[red]✗ Ask error: {e}[/red]")
                    if self._app: self._app.invalidate()
                if self._app:
                    self._app.loop.call_soon_threadsafe(_err)
                else:
                    _err()

        threading.Thread(target=_run, daemon=True).start()

    # ── command handler ───────────────────────────────────────────────────────

    def _handle_cmd(self, raw: str) -> None:
        raw  = (raw or "").strip()
        root = _project_root_default()

        if self._task_mode_pending is not None:
            mode = self._task_mode_pending
            self._task_mode_pending = None
            if not raw:
                self._write(f"[dim]  No task entered[/dim]")
                return
            self._do_new_task(raw, mode, root)
            return

        # ── Clarification response handler ────────────────────────────────────
        if self._clarif_mode:
            clarif = self._clarif_data
            opts   = clarif.get("options", [])
            o1     = opts[0] if len(opts) > 0 else ""
            o2     = opts[1] if len(opts) > 1 else ""
            answer: str | None = None

            if raw == "1" and o1:
                answer = f"Lựa chọn 1: {o1}"
            elif raw == "2" and o2:
                answer = f"Lựa chọn 2: {o2}"
            elif raw.startswith("/btw "):
                answer = raw[5:].strip()
            elif raw == "/skip" or raw == "skip":
                answer = "__skip__"
            elif raw:
                # Let other commands through (exit, etc.) but keep clarif mode
                pass

            if answer is not None:
                # Write decision to history
                self._clarif_mode = False
                self._clarif_data = {}
                if answer == "__skip__":
                    self._write(f"[dim]└──[/dim] [dim]Bỏ qua → chọn phương án đơn giản nhất[/dim]")
                elif answer.startswith("Lựa chọn"):
                    self._write(f"[dim]└──[/dim] [bold]Bạn chọn:[/bold] {answer[9:]}")
                else:
                    self._write(f"[dim]└──[/dim] [bold]Nói thêm:[/bold] {answer[:100]}")
                self._set_live("")
                try:
                    ws.answer_clarification(answer)
                except Exception:
                    pass
                return
        # ──────────────────────────────────────────────────────────────────────

        if raw.startswith("/ask"):
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", ""):
                self._write(f"[dim]✗ Pipeline agent đang chạy — không thể ask trong lúc này[/dim]")
                return
            if self._ask_thinking:
                self._write(f"[dim]✗ /ask đang xử lý — chờ response trước[/dim]")
                return
            text = raw[4:].strip()
            if not text:
                self._write(f"[dim]✗ Usage: /ask <question>  — nhập câu hỏi ngay sau /ask[/dim]")
                return
            self._do_new_task(text, "ask", root)
            return

        if raw.startswith("/agent"):
            if self._ask_thinking:
                self._write(f"[dim]✗ /ask đang xử lý — chờ response trước[/dim]")
                return
            text = raw[6:].strip()
            if not text:
                self._write(f"[dim]✗ Usage: /agent <task>  — nhập task ngay sau /agent[/dim]")
                return
            self._do_new_task(text, "agent", root)
            return

        if raw.startswith("/") and len(raw) > 1:
            self._write(f"[dim]✗ Unknown mode '{raw.split()[0]}'. Use /ask or /agent[/dim]")
            return

        if self._exit_confirm_mode:
            self._exit_confirm_mode = False
            if raw.lower() in ("y", "yes"):
                self._do_cleanup_exit()
            else:
                self._write(f"[dim]  Cancelled[/dim]")
            return

        if self._post_delete_mode:
            self._post_delete_mode = False
            if not raw or raw.lower() in ("n", "no"):
                # Write final state to history (replacing live section visual)
                self._write(f"[red]✗[/red] [bold]Human Gate[/bold]  [dim]Declined[/dim]")
                self._gate_state = _GATE_WAITING
                self._start_decline_countdown()
            elif raw.lower() in ("y", "yes"):
                self._attempt_count += 1
                self._gate_state        = _GATE_REGEN
                self._last_active_step  = ""
                self._shown_file_events = []
                self._write(f"[red]●[/red] [bold]Human Gate[/bold]")
                self._write(f"[dim]└──[/dim] [red]Đã từ chối[/red]")
                self._write(f"[dim]   └──[/dim] [bold green]●[/bold green] [green]Đã chọn regenerate[/green] (attempt {self._attempt_count})")
                if self._last_task_text:
                    ws.reset_pipeline_visual()
                    ws.set_pipeline_run_finished(False)
                    from core.cli.python_cli.flows.start_flow import start_pipeline_from_tui
                    start_pipeline_from_tui(self._last_task_text, root, "agent")
                    self._pipeline_pending = True
                else:
                    self._write(f"[dim]  No previous task — use /agent <task>[/dim]")
            else:
                self._do_new_task(raw, "agent", root)
            return

        if not raw:
            snap_e = ws.get_pipeline_snapshot()
            active_e = str(snap_e.get("active_step") or "idle")
            if active_e not in ("idle", "end_failed", "") or self._ask_thinking:
                self._write(f"[dim]Mode đang chạy ({active_e}) — chờ hoàn thành[/dim]", indent=True)
            else:
                # Empty Enter when idle → auto enter /ask mode
                self._ask_thinking = True
                self._write(f"[bold #7aa2f7]you:[/bold #7aa2f7]", indent=True)
                self._write(f"[dim]   (nhập câu hỏi tiếp theo — ask mode)[/dim]", indent=True)
                self._ask_thinking = False
                # Actually start ask with empty → show hint
                self._write(f"[dim]  Tip: /ask <câu hỏi>  hoặc  /agent <task>[/dim]", indent=True)
            return

        parts = raw.split(None, 1)
        cmd   = parts[0].lower()
        rest  = parts[1].strip() if len(parts) > 1 else ""

        try:
            from core.cli.python_cli.state import log_system_action
            log_system_action("monitor.input", raw[:300])
        except Exception:
            pass

        if cmd in ("exit", "quit", "q", "back"):
            # Always exit immediately — no y/n
            try:
                ws.request_pipeline_stop()
            except Exception:
                pass
            try:
                from core.cli.python_cli.flows.context.monitor_actions import apply_context_delete_from_monitor
                apply_context_delete_from_monitor(_project_root_default())
            except Exception:
                pass
            ws.reset_pipeline_visual()
            if self._app:
                self._app.exit()
            return

        if cmd == "check":
            self._open_check(root)
            return

        if cmd == "accept":
            snap = ws.get_pipeline_snapshot()
            if not snap.get("paused_at_gate"):
                self._write(f"[dim]✗ No pending gate[/dim]")
                return
            self._gate_state = _GATE_ACCEPTED
            self._write("")
            self._write(f"[bold green]●[/bold green] [bold]Human Gate[/bold]")
            self._write(f"[dim]└──[/dim] [green]Accepting context.md…[/green]  [bold green]●[/bold green]")
            self._scroll_offset = 0

            def _accept_bg():
                try:
                    from core.cli.python_cli.flows.context.monitor_actions import apply_context_accept_from_monitor
                    apply_context_accept_from_monitor(root)
                except Exception:
                    pass
            threading.Thread(target=_accept_bg, daemon=True).start()
            return

        if cmd == "delete":
            try:
                from core.cli.python_cli.flows.context.monitor_actions import apply_context_delete_from_monitor
                apply_context_delete_from_monitor(root)
                # Set gate state — live section will show the declined UI immediately
                # (no _write to history to avoid duplicate with live section)
                self._gate_state       = _GATE_DECLINED
                self._post_delete_mode = True
                self._scroll_offset    = 0
            except Exception as e:
                self._write(f"[red]✗ Delete failed: {e}[/red]")
            return

        if cmd == "task":
            if not rest:
                self._write(f"[dim]  Tip: /ask <q>  or  /agent <task>[/dim]")
                return
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle",):
                self._write(f"[dim]✗ Pipeline running[/dim]")
                return
            task_parts = rest.rsplit(None, 1)
            if len(task_parts) == 2 and task_parts[1].lower() in ("ask", "agent"):
                task_text, task_mode = task_parts[0].strip(), task_parts[1].lower()
            else:
                task_text, task_mode = rest, "agent"
            self._do_new_task(task_text, task_mode, root)
            return

        if cmd == "log":
            self._write("")
            self._write(f"[dim]── activity log ──[/dim]")
            try:
                from ..runtime.activity_log import format_activity_lines, list_recent_activity
                lines = format_activity_lines(list_recent_activity(limit=50, min_ts=_activity_min_ts_kw()), "")
                for line in lines[-20:]:
                    self._write(f"[dim]{line}[/dim]")
            except Exception as e:
                self._write(f"[dim]  (log error: {e})[/dim]")
            self._scroll_offset = 0
            return

        if cmd == "info":
            snap = ws.get_pipeline_snapshot()
            tier = snap.get("brief_tier")
            try:
                from .monitor_helpers import _steps_for_tier, _pipeline_info_lines, _parse_token_counts_for_node
                steps = _steps_for_tier(tier)
                self._write("")
                for line in _pipeline_info_lines(tier, steps):
                    self._write(line)
                _GEN = ("ambassador", "leader_generate", "expert_solo", "expert_coplan")
                pt_t, ct_t = 0, 0
                for sid in [s for s in steps if s in _GEN]:
                    pt, ct = _parse_token_counts_for_node(sid)
                    if pt or ct:
                        self._write(f"  [dim]{_ROLE.get(sid, sid):<14}  in:{pt:,}  out:{ct:,}[/dim]")
                        pt_t += pt; ct_t += ct
                if pt_t or ct_t:
                    self._write(f"  [dim]{'Total':<14}  in:{pt_t:,}  out:{ct_t:,}[/dim]")
            except Exception as e:
                self._write(f"[dim]  (info: {e})[/dim]")
            self._scroll_offset = 0
            return

        if cmd == "btw":
            if not rest:
                self._write(f"[dim]✗ btw chưa có nội dung — nhập: btw <ghi chú>[/dim]")
                return
            snap = ws.get_pipeline_snapshot()
            # Restrict btw to active pipeline only
            if str(snap.get("active_step") or "idle") in ("idle", "end_failed", ""):
                self._write(f"[dim]✗ Pipeline không chạy — btw chỉ dùng khi pipeline đang generate[/dim]")
                self._write(f"[dim]  Dùng /ask để hỏi hoặc /agent <task> để bắt đầu pipeline[/dim]")
                return
            # P3: go directly to leader model, not CompactWorker
            self._handle_btw_inline(rest, snap)
            return

        # Plain text → inline ask (when pipeline is idle)
        snap_now   = ws.get_pipeline_snapshot()
        active_now = str(snap_now.get("active_step") or "idle")
        if active_now not in ("idle", "end_failed", ""):
            self._write(f"[dim]  btw <ghi chú>  để ghi chú khi pipeline đang chạy[/dim]")
            return
        if self._ask_thinking:
            self._write(f"[dim]✗ /ask đang xử lý — chờ response trước[/dim]")
            return
        self._handle_ask_inline(raw)



    def _render_clarification(self, clarif: dict) -> None:
        """Display clarification UI in live step — matches gen step style."""
        sc       = _SPINNER[self._spin % len(_SPINNER)]
        q        = clarif.get("question", "Bạn muốn cụ thể là gì?")
        opts     = clarif.get("options", [])
        o1       = opts[0] if len(opts) > 0 else "Phương án 1"
        o2       = opts[1] if len(opts) > 1 else "Phương án 2"

        parts = [
            f"[#888888]{sc}[/#888888] [bold]Leader[/bold]  [dim][cần thêm thông tin][/dim]",
            f"[dim]└──[/dim] [bold yellow]{q}[/bold yellow]",
            f"[dim]    ├── [bold]1[/bold][/dim]  {o1}",
            f"[dim]    ├── [bold]2[/bold][/dim]  {o2}",
            f"[dim]    └── [bold]/btw[/bold] <nói thêm>  ·  [bold]/skip[/bold] → chọn đơn giản nhất[/dim]",
        ]
        self._set_live("\n".join(parts))

    def _handle_btw_inline(self, msg: str, snap: dict) -> None:
        """P3: btw goes directly to leader model (no CompactWorker).
        Shows note (max 12 lines), streams thinking in live branch, shows answer.
        """
        active = str(snap.get("active_step") or "idle")
        tier   = snap.get("brief_tier")

        # P3.1: Format note display (max 12 lines)
        raw_lines    = msg.strip().split("\n")
        disp_lines   = raw_lines[:12]
        was_truncated = len(raw_lines) > 12
        note_preview  = "\n".join(f"[dim]  {ln[:100]}[/dim]" for ln in disp_lines)

        # P3.2: Which role is processing?
        role_name = _ROLE.get(active, "Leader") if active in _GEN_STEPS else "Leader"
        try:
            from .monitor_helpers import _model_for_step
            model_short = _model_for_step(active, tier) or "leader"
        except Exception:
            model_short = "leader"

        self._write("")
        self._write(
            f"[dim]── btw  {time.strftime('%H:%M:%S')}"
            f"  [bold]{role_name}[/bold] xem  ·  {model_short} ──[/dim]"
        )
        for ln in disp_lines:
            self._write(f"[dim]  {ln[:100]}[/dim]")
        if was_truncated:
            self._write(f"[dim]  … ({len(raw_lines)-12} dòng ẩn — model xem được toàn bộ)[/dim]")

        sc = _SPINNER[self._spin % len(_SPINNER)]
        self._set_live(
            f"[dim]{sc}[/dim] [bold]{role_name}[/bold]\n"
            f"[dim]└── đang xem btw…[/dim]"
        )

        def _run() -> None:
            try:
                from ._btw_inline import stream_btw_response

                chunks: list[str] = []
                for text in stream_btw_response(
                    active=active, tier=tier, role_name=role_name, note=msg
                ):
                    chunks.append(text)
                    so_far   = "".join(chunks)
                    ln_so_far = [l for l in so_far.split("\n") if l.strip()]
                    last6    = ln_so_far[-6:]
                    spin_c   = _SPINNER[self._spin % len(_SPINNER)]
                    live_parts = [
                        f"[dim]{spin_c}[/dim] [bold]{role_name}[/bold]",
                        f"[dim]└── đang nghĩ về btw…[/dim]",
                    ]
                    if last6:
                        live_parts.append(f"[dim]    └── {last6[0][:96]}[/dim]")
                        for l in last6[1:]:
                            live_parts.append(f"[dim]        {l[:96]}[/dim]")
                    def _upd(pts=live_parts):
                        self._set_live("\n".join(pts))
                        if self._app: self._app.invalidate()
                    if self._app:
                        self._app.loop.call_soon_threadsafe(_upd)

                # P3.5: Done — collapse thinking, show answer
                answer = "".join(chunks).strip()

                def _show():
                    self._set_live("")  # collapse thinking branch
                    if answer:
                        # Word-wrap answer
                        words, curr, wchunks = answer.split(), "", []
                        for w in words:
                            if len(curr) + len(w) + 1 > 100:
                                wchunks.append(curr); curr = w
                            else:
                                curr = (curr + " " + w).strip()
                        if curr:
                            wchunks.append(curr)
                        self._write(f"[dim]└──[/dim] [bold]{role_name}[/bold] [dim](btw)[/dim]")
                        for i, wc in enumerate(wchunks):
                            pfx = "[dim]    └──[/dim]" if i == 0 else "[dim]       [/dim]"
                            self._write(f"{pfx} [dim]{wc}[/dim]")
                    else:
                        # P3.6: no answer = model declined
                        self._write(f"[dim]└── {role_name} không có phản hồi cho btw này[/dim]")
                    if self._app: self._app.invalidate()

                if self._app:
                    self._app.loop.call_soon_threadsafe(_show)
                else:
                    _show()

            except Exception as e:
                def _err():
                    self._set_live("")
                    self._write(f"[red]✗ btw error: {e}[/red]")
                    if self._app: self._app.invalidate()
                if self._app:
                    self._app.loop.call_soon_threadsafe(_err)
                else:
                    _err()

        threading.Thread(target=_run, daemon=True).start()

    def _do_new_task(self, task_text: str, task_mode: str, root: str) -> None:
        self._last_task_text = task_text
        self._attempt_count  = 1
        self._gate_state     = _GATE_WAITING
        self._scroll_offset  = 0

        # Agent mode always runs pipeline — no auto-detect to ask
        # Use /ask <question> explicitly for ask mode
        if task_mode == "ask":
            self._handle_ask_inline(task_text)
            return

        self._write("")
        self._write(f"[bold cyan]●[/bold cyan] [bold]Task started[/bold] [agent] — {time.strftime('%H:%M:%S')}")
        self._write(f"  [dim]{task_text[:200]}[/dim]")

        ws.reset_pipeline_visual()
        ws.set_pipeline_run_finished(False)
        self._last_active_step  = ""
        self._shown_file_events = []
        from core.cli.python_cli.flows.start_flow import start_pipeline_from_tui
        start_pipeline_from_tui(task_text, root, task_mode)
        self._pipeline_pending = True

    # ── entry point ───────────────────────────────────────────────────────────

    def run(self) -> None:
        self._replay_history()
        self._app = self._build_app()

        async def _main():
            task = asyncio.create_task(self._tick_loop())
            try:
                await self._app.run_async()
            finally:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        try:
            import sys
            asyncio.run(_main())
        finally:
            import sys
            sys.stdout.write("\033[?25h\033[0m")
            sys.stdout.flush()


def run_workflow_list_view(project_root: str) -> None:
    ws.set_workflow_project_root(project_root)
    ws.apply_stale_workflow_ui_if_needed(project_root)
    WorkflowListApp().run()
