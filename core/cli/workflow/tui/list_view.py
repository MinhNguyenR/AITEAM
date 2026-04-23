"""Textual TUI — workflow LIST monitor.

Layout
------
Header (clock)
  hint bar       — step · tier · token status  (1 line)
  stream panel   — completion events history (scrollable)
  active node    — compact "Role — what AI is doing" + 3-line LLM branch
  hints bar      — command reference  (1 line)
  cmd input      — dock bottom

Commands
  task <text> [ask|agent] · accept · delete · check · log · btw [msg] · exit
"""

from __future__ import annotations

import threading
import time

from rich.text import Text
from textual.app import App, ComposeResult, on
from textual.binding import Binding
from textual.widgets import Footer, Header, Input, RichLog, Static

from core.cli.state import log_system_action

from ..runtime import session as ws
from .monitor_helpers import (
    TOKEN_WARN_THRESHOLD,
    _activity_min_ts_kw,
    _match_notification_id,
    _parse_file_events,
    _parse_token_counts,
    _project_root_default,
    _role_subtitle,
)
from .monitor_screens import (
    ActivityLogScreen,
    CheckpointSearchScreen,
    ConfirmExitScreen,
    ContextFilePreviewScreen,
    ContextReviewScreen,
)

_GEN_STEPS = frozenset({"ambassador", "leader_generate", "expert_solo", "expert_coplan"})
_SPINNER_CHARS = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_STEP_TASKS: dict[str, str] = {
    "ambassador":         "parsing & routing task",
    "leader_generate":    "generating context.md",
    "expert_solo":        "generating context.md",
    "expert_coplan":      "co-planning context",
    "human_context_gate": "waiting for review",
    "finalize_phase1":    "finalizing pipeline",
}

_CMD_HINT = "task <text> [mode] · accept · delete · check · log · btw [msg] · exit"


class WorkflowListApp(App[None]):
    CSS = """
    Screen { background: #000000; }
    #hint {
        background: #111111; color: #c8d3f5;
        padding: 0 1; height: 1;
    }
    #stream_panel {
        height: 1fr;
        background: #000000;
    }
    #active_node {
        background: #000000; padding: 0 1;
        height: auto; min-height: 0; border: none;
    }
    #hints_bar {
        background: #111111; color: #565f89;
        padding: 0 2; height: 1;
    }
    #cmd_input {
        dock: bottom; margin: 0 1;
        height: 3; border: solid #3b4261;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._spin_idx = 0
        self._gate_shown: bool = False
        self._seen_activity_min_ts: float | None = None
        self._last_active_step: str = ""
        self._shown_file_events: list[tuple[str, str]] = []
        self._token_warned: bool = False
        self._error_locked: bool = False
        self._seen_running: bool = False
        self._post_delete_mode: bool = False
        self._last_task_text: str = ""

    # ── compose ──────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static(id="hint")
        yield RichLog(
            id="stream_panel",
            highlight=False, markup=True,
            wrap=True, auto_scroll=False,
        )
        yield Static(id="active_node", expand=True)
        yield Static(f"[dim]{_CMD_HINT}[/dim]", id="hints_bar")
        yield Input(id="cmd_input", placeholder="command…")
        yield Footer()

    # ── lifecycle ────────────────────────────────────────────────────────

    def action_quit(self) -> None:
        snap = ws.get_pipeline_snapshot()
        active = str(snap.get("active_step") or "idle")
        if active not in ("idle", "end_failed", ""):
            self.push_screen(ConfirmExitScreen(), callback=self._on_exit_confirmed)
            return
        self.exit()

    def action_refresh(self) -> None:
        self._refresh_views()

    def on_mount(self) -> None:
        ws.apply_stale_workflow_ui_if_needed(_project_root_default())
        self.set_interval(0.25, self._tick_refresh)
        self._refresh_views()
        self._focus_cmd()

    def _focus_cmd(self) -> None:
        try:
            self.query_one("#cmd_input", Input).focus()
        except LookupError:
            pass

    def _on_exit_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self._cleanup_and_exit()
        else:
            self._focus_cmd()

    def _cleanup_and_exit(self) -> None:
        try:
            from core.cli.flows.context.monitor_actions import apply_context_delete_from_monitor
            apply_context_delete_from_monitor(_project_root_default())
        except Exception:
            pass
        self.exit()

    def _show_error(self, msg: str) -> None:
        self._error_locked = True
        try:
            inp = self.query_one("#cmd_input", Input)
            inp.placeholder = f"⚠ {msg}  (Enter to dismiss)"
            inp.value = ""
        except LookupError:
            pass

    def _clear_error(self) -> None:
        self._error_locked = False
        try:
            inp = self.query_one("#cmd_input", Input)
            inp.placeholder = "command…"
        except LookupError:
            pass

    # ── tick ─────────────────────────────────────────────────────────────

    def _tick_refresh(self) -> None:
        self._spin_idx += 1
        snap = ws.get_pipeline_snapshot()
        active = str(snap.get("active_step") or "idle")
        if active not in ("idle", "end_failed", "") or snap.get("ambassador_status") == "running":
            self._seen_running = True
        if self._seen_running and snap.get("run_finished") and not snap.get("paused_at_gate"):
            self._flush_final(snap)
            self.exit()
            return
        self._refresh_views()
        self._maybe_auto_open_gate(snap)

    def _maybe_auto_open_gate(self, snap: dict) -> None:
        if not snap.get("paused_at_gate"):
            self._gate_shown = False
            return
        if self._gate_shown:
            return
        try:
            from core.cli.flows.context_flow import find_context_md, is_no_context
        except ImportError:
            return
        ctx = find_context_md(_project_root_default())
        if not ctx or is_no_context(ctx):
            return
        self._gate_shown = True
        self.push_screen(ContextReviewScreen(_project_root_default()))

    # ── main render ──────────────────────────────────────────────────────

    def _refresh_views(self) -> None:
        ws.prune_stale_pipeline_notifications()
        ws.apply_stale_workflow_ui_if_needed(_project_root_default())

        snap = ws.get_pipeline_snapshot()
        tier = snap.get("brief_tier")
        toast_txt = str(snap.get("toast") or "")
        buf = str(snap.get("leader_stream_buffer") or "")
        active = str(snap.get("active_step") or "idle")

        # ── activity min_ts reset ──
        mt_kw = _activity_min_ts_kw() or 0.0
        if self._seen_activity_min_ts is None:
            self._seen_activity_min_ts = mt_kw
        elif mt_kw > self._seen_activity_min_ts + 1e-9:
            self._seen_activity_min_ts = mt_kw
            self._last_active_step = ""
            self._shown_file_events = []
            self._token_warned = False

        pt, ct = _parse_token_counts()

        # ── token warning ──
        total_tok = pt + ct
        if total_tok > TOKEN_WARN_THRESHOLD and not self._token_warned:
            self._token_warned = True
            slog = self.query_one("#stream_panel", RichLog)
            slog.write(f"[bold yellow]⚠ Token budget: {total_tok:,} / 262k — consider 'btw compact'[/bold yellow]")

        # ── hint bar ──
        hint_parts: list[str] = []
        if toast_txt.strip():
            hint_parts.append(f"[bold #e0af68]{toast_txt}[/bold #e0af68]  ")
        spin_char = _SPINNER_CHARS[self._spin_idx % len(_SPINNER_CHARS)]
        tok_s = f"  [dim]in:{pt:,} out:{ct:,}[/dim]" if (pt or ct) else ""
        active_display = (
            f"[grey50]{spin_char}[/grey50] [yellow]{active}[/yellow]"
            if active not in ("idle", "end_failed", "")
            else f"[dim]{active}[/dim]"
        )
        hint_parts.append(
            f"[bold #7aa2f7]list[/bold #7aa2f7]"
            f"  {active_display}"
            f"  Tier {tier or '—'}"
            f"{tok_s}"
        )
        self.query_one("#hint", Static).update("".join(hint_parts))

        slog = self.query_one("#stream_panel", RichLog)

        # ── stream: step transition events (completion markers) ──
        if active != self._last_active_step:
            if self._last_active_step in _GEN_STEPS:
                label = _STEP_TASKS.get(self._last_active_step, self._last_active_step)
                role = _role_subtitle(self._last_active_step, tier, "") if self._last_active_step in _GEN_STEPS else ""
                role_prefix = f"[bold #7aa2f7]{role}[/bold #7aa2f7] — " if role else ""
                tok_done = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
                slog.write("")
                slog.write(f"[bold green]● {role_prefix}{label} complete — {time.strftime('%H:%M:%S')}[/bold green]{tok_done}")
            if active == "human_context_gate":
                slog.write("")
                slog.write(
                    f"[bold yellow]◉ waiting for context review — {time.strftime('%H:%M:%S')}[/bold yellow]"
                    f"  [dim](accept · delete · check)[/dim]"
                )
            elif active == "finalize_phase1":
                slog.write("")
                slog.write(f"[dim]── finalizing ──[/dim]")
            self._last_active_step = active

        # ── stream: file write events ──
        file_evs = _parse_file_events()
        new_file_evs = file_evs[len(self._shown_file_events):]
        tok_ev = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
        for node, detail in new_file_evs:
            slog.write(f"[bold green]✓ {detail}[/bold green]  [dim]{node}[/dim]{tok_ev}")
        if new_file_evs:
            self._shown_file_events = file_evs

        # ── active node: compact live display (with role name) ──
        self._update_active_node(active, buf, pt, ct, tier)

    def _update_active_node(self, active: str, buf: str, pt: int, ct: int, tier: str | None) -> None:
        spin_char = _SPINNER_CHARS[self._spin_idx % len(_SPINNER_CHARS)]

        if active in ("idle", "", "end_failed"):
            self.query_one("#active_node", Static).update("")
            return

        task_label = _STEP_TASKS.get(active, active)
        buf_lines = [ln for ln in buf.split("\n") if ln.strip()] if buf else []
        last_3 = buf_lines[-3:]

        sc = f"[#888888]{spin_char}[/#888888]"

        if active in _GEN_STEPS:
            role = _role_subtitle(active, tier, "")
            tok_s = f"  [dim](in:{pt:,}  out:{ct:,}  context.md)[/dim]" if (pt or ct) else ""
            if role:
                # Tree: role on top line, task branches below
                parts = [f"{sc} [bold #7aa2f7]{role}[/bold #7aa2f7]"]
                parts.append(f"[dim]└─[/dim] {task_label}{tok_s}")
                if last_3:
                    for line in last_3:
                        parts.append(f"[dim]   │  {line[:98]}[/dim]")
            else:
                parts = [f"{sc} {task_label}{tok_s}"]
                if last_3:
                    parts.append("[dim]│[/dim]")
                    for line in last_3:
                        parts.append(f"[dim]│  {line[:100]}[/dim]")
        elif active == "human_context_gate":
            parts = ["[yellow]◉[/yellow] [bold]waiting for review[/bold]  [dim](accept · delete · check)[/dim]"]
        elif active == "finalize_phase1":
            parts = [f"{sc} [dim]finalizing pipeline…[/dim]"]
        else:
            parts = [f"{sc} [dim]{task_label}[/dim]"]

        self.query_one("#active_node", Static).update(Text.from_markup("\n".join(parts)))

    def _flush_final(self, snap: dict) -> None:
        slog = self.query_one("#stream_panel", RichLog)
        pt, ct = _parse_token_counts()
        tok_s = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
        file_evs = _parse_file_events()
        for node, detail in file_evs[len(self._shown_file_events):]:
            slog.write(f"[bold green]✓ {detail}[/bold green]  [dim]{node}[/dim]{tok_s}")
        slog.write("")
        slog.write(f"[bold green]✓ Pipeline complete — {time.strftime('%H:%M:%S')}[/bold green]")

    # ── commands ─────────────────────────────────────────────────────────

    @on(Input.Submitted, "#cmd_input")
    def _on_cmd(self, event: Input.Submitted) -> None:
        raw = (event.value or "").strip()
        event.input.value = ""

        if self._error_locked:
            if not raw:
                self._clear_error()
            return

        root = _project_root_default()

        # ── inline y/n after delete ──
        if self._post_delete_mode:
            self._post_delete_mode = False
            try:
                self.query_one("#cmd_input", Input).placeholder = "command…"
            except LookupError:
                pass
            slog = self.query_one("#stream_panel", RichLog)
            if not raw or raw.lower() in ("n", "no"):
                slog.write("[dim]  Skipped — use 'task <text>' to start new[/dim]")
            elif raw.lower() in ("y", "yes"):
                if self._last_task_text:
                    slog.write(f"[cyan]  ↳ Regenerating…[/cyan]")
                    ws.reset_pipeline_visual()
                    ws.set_pipeline_run_finished(False)
                    from core.cli.flows.start_flow import start_pipeline_from_tui
                    start_pipeline_from_tui(self._last_task_text, root, "agent")
                    self._seen_running = True
                else:
                    slog.write("[dim]  No previous task recorded — use 'task <text>'[/dim]")
            else:
                self._last_task_text = raw
                slog.write(f"[bold cyan]● Task started [agent] — {time.strftime('%H:%M:%S')}[/bold cyan]")
                slog.write(Text(raw[:200]))
                ws.reset_pipeline_visual()
                ws.set_pipeline_run_finished(False)
                from core.cli.flows.start_flow import start_pipeline_from_tui
                start_pipeline_from_tui(raw, root, "agent")
                self._seen_running = True
            return

        if not raw:
            return

        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        log_system_action("monitor.input", raw[:300])

        if cmd in ("exit", "quit", "q", "back"):
            snap = ws.get_pipeline_snapshot()
            active = str(snap.get("active_step") or "idle")
            if active not in ("idle", "end_failed", ""):
                self.push_screen(ConfirmExitScreen(), callback=self._on_exit_confirmed)
            else:
                self.exit()
            return

        if cmd == "log":
            self.push_screen(ActivityLogScreen())
            self.set_timer(0.05, self._focus_cmd)
            return

        if cmd in ("search", "model"):
            self.push_screen(CheckpointSearchScreen(rest))
            self.set_timer(0.05, self._focus_cmd)
            return

        if cmd == "check":
            self.push_screen(ContextReviewScreen(root))
            self.set_timer(0.05, self._focus_cmd)
            return

        if cmd == "accept":
            snap = ws.get_pipeline_snapshot()
            if not snap.get("paused_at_gate"):
                self._show_error("No pending gate — pipeline is not paused for review")
                return
            slog = self.query_one("#stream_panel", RichLog)
            slog.write("")
            slog.write(f"[bold green]● Accepting context.md — {time.strftime('%H:%M:%S')}[/bold green]")
            self._gate_shown = True

            def _accept_bg() -> None:
                try:
                    from core.cli.flows.context.monitor_actions import apply_context_accept_from_monitor
                    apply_context_accept_from_monitor(root)
                except Exception:
                    pass

            threading.Thread(target=_accept_bg, daemon=True).start()
            return

        if cmd == "delete":
            slog = self.query_one("#stream_panel", RichLog)
            try:
                from core.cli.flows.context.monitor_actions import apply_context_delete_from_monitor
                apply_context_delete_from_monitor(root)
                slog.write("")
                slog.write(f"[bold yellow]● context.md deleted — {time.strftime('%H:%M:%S')}[/bold yellow]")
                self._post_delete_mode = True
                if self._last_task_text:
                    slog.write(f"[dim]  Regenerate '{self._last_task_text[:60]}'? (y/n)[/dim]")
                else:
                    slog.write(f"[dim]  Regenerate? Type y, n, or new task text[/dim]")
                try:
                    self.query_one("#cmd_input", Input).placeholder = "y / n / <new task text>"
                except LookupError:
                    pass
            except Exception as e:
                slog.write(f"[red]● Delete failed: {e}[/red]")
            return

        if cmd == "task":
            if not rest:
                self._show_error("Usage: task <text> [ask|agent]  (default: agent)")
                return
            snap = ws.get_pipeline_snapshot()
            active = str(snap.get("active_step") or "idle")
            if active not in ("idle",):
                self._show_error(f"Pipeline running ({active}) — wait or use 'btw <msg>'")
                return
            task_parts = rest.rsplit(None, 1)
            if len(task_parts) == 2 and task_parts[1].lower() in ("ask", "agent"):
                task_text = task_parts[0].strip()
                task_mode = task_parts[1].lower()
            else:
                task_text = rest
                task_mode = "agent"

            self._last_task_text = task_text
            slog = self.query_one("#stream_panel", RichLog)

            # Question detection: route to ask mode via drain queue
            if task_mode == "agent":
                try:
                    from core.cli.flows.start_flow import _looks_like_chat_intent
                    from core.cli.flows.ask_flow import looks_like_code_intent
                    if _looks_like_chat_intent(task_text) and not looks_like_code_intent(task_text):
                        slog.write("")
                        slog.write(f"[dim]  Question detected → switching to ask mode…[/dim]")
                        ws.enqueue_monitor_command("start_workflow", {"prompt": task_text, "mode": "ask", "project_root": root})
                        self.set_timer(0.3, self.exit)
                        return
                except Exception:
                    pass

            slog.write("")
            slog.write(f"[bold cyan]● Task started [{task_mode}] — {time.strftime('%H:%M:%S')}[/bold cyan]")
            slog.write(Text(task_text[:200]))

            ws.reset_pipeline_visual()
            ws.set_pipeline_run_finished(False)
            from core.cli.flows.start_flow import start_pipeline_from_tui
            start_pipeline_from_tui(task_text, root, task_mode)
            self._seen_running = True
            return

        if cmd == "dismiss":
            nid = _match_notification_id(rest) or rest
            if not nid:
                self._show_error("Usage: dismiss <id>")
                return
            ws.dismiss_pipeline_notification(nid)
            self.notify(f"Dismissed {nid[:8]}")
            return

        if cmd == "view":
            nid = _match_notification_id(rest) or rest
            if not nid:
                self._show_error("Usage: view <id>")
                return
            for n in ws.list_active_notifications():
                if str(n.get("id", "")).startswith(nid):
                    extra = n.get("extra") if isinstance(n.get("extra"), dict) else {}
                    p = str(extra.get("context_path") or extra.get("state_path") or "")
                    if p:
                        self.push_screen(ContextFilePreviewScreen(p))
                        self.set_timer(0.05, self._focus_cmd)
                        return
            self._show_error(f"Not found: {nid}")
            return

        if cmd == "btw":
            snap = ws.get_pipeline_snapshot()
            active = str(snap.get("active_step") or "idle")
            slog = self.query_one("#stream_panel", RichLog)
            slog.write("")
            slog.write(
                f"[dim]── btw  {time.strftime('%H:%M:%S')}"
                f"  {active}  Tier {snap.get('brief_tier') or '—'} ──[/dim]"
            )
            if rest:
                if active not in ("idle",):
                    slog.write(f"[dim yellow]  pipeline active — note queued[/dim yellow]")

                def _run_btw(msg=rest, _snap=snap, _slog=slog) -> None:
                    try:
                        from agents.compact_worker import CompactWorker, build_state_summary_for_btw
                        cw = CompactWorker()
                        summary = build_state_summary_for_btw(_snap)
                        result = cw.process_btw(msg, summary)
                        self.call_from_thread(
                            _slog.write,
                            f"[cyan]  ↳ [CompactWorker] {result[:300]}[/cyan]"
                        )
                        ws.enqueue_monitor_command("btw_note", {"note": result, "raw": msg})
                    except Exception as e:
                        self.call_from_thread(
                            _slog.write,
                            f"[dim red]  btw failed: {e}[/dim red]"
                        )

                threading.Thread(target=_run_btw, daemon=True).start()
            self._refresh_views()
            return

        self._show_error(f"Unknown: '{cmd}'  —  {_CMD_HINT}")


# ── entry point (keeps existing signature) ───────────────────────────────────

def run_workflow_list_view(project_root: str) -> None:
    ws.set_workflow_project_root(project_root)
    ws.apply_stale_workflow_ui_if_needed(project_root)
    WorkflowListApp().run()
