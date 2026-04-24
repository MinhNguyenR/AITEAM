"""Textual TUI — workflow CHAIN monitor.

Pure terminal style — no Header, no Footer, no palette, no chrome.

Layout
------
  #hint         — 1 line: chain · step · tier · in:X out:Y  (spinner here)
  #pipeline_bar — 2 lines: [Ambassador ⠋] ─── [Leader ○] ─── ... (fixed chain)
  #scroll_area  (VerticalScroll, 1fr)
      #stream_panel (RichLog, height:auto) — completed step history
      #live_step   (Static,  height:auto) — live current step (updates every 0.25s)
  #cmd_input    — 3 lines: docked input

Animation
---------
  #live_step replaces content every 0.25s — braille spinner looks animated.
  When step completes → write ONE green completion line to RichLog, clear live_step.
  Zero duplicates. Chain bar shows overall progress as colored dots.

Tree format (live_step)
---------
  Generate context.md  (token in: 736  token out: 101  role: Leader)  ⠋
  └── first line of buffer
      second line
      third line
      ... (6 latest lines, └── only on first)

Commands
--------
  task <text> [ask|agent] · accept · delete · check · log · btw [msg] · exit
"""

from __future__ import annotations

import threading
import time

from rich.text import Text
from textual.app import App, ComposeResult, on
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Input, RichLog, Static

from core.cli.pythonCli.state import log_system_action

from ..runtime import session as ws
from .monitor_helpers import (
    TOKEN_WARN_THRESHOLD,
    _activity_min_ts_kw,
    _build_pipeline_markup,
    _compute_visual_states,
    _event_sequence_warning,
    _match_notification_id,
    _parse_file_events,
    _parse_token_counts,
    _project_root_default,
    _steps_for_tier,
)
from .monitor_screens import (
    ActivityLogScreen,
    CheckpointSearchScreen,
    ContextFilePreviewScreen,
    ContextReviewScreen,
)

_GEN_STEPS = frozenset({"ambassador", "leader_generate", "expert_solo", "expert_coplan"})
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

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

_CMD_HINT = "task <text> [mode] · accept · delete · check · log · btw [msg] · exit"


class WorkflowMonitorApp(App[None]):
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Screen { background: #000000; }

    #hint {
        height: 1; background: #0a0a0a; color: #c8d3f5; padding: 0 1;
    }
    #pipeline_bar {
        height: 2; background: #0a0a0a; padding: 0 2;
        border-bottom: solid #111122;
    }
    #scroll_area {
        height: 1fr; background: #000000;
    }
    #stream_panel {
        height: auto; min-height: 0;
        background: #000000;
        scrollbar-size: 0 0;
        scrollbar-size-vertical: 0;
    }
    #live_step {
        height: auto; min-height: 0;
        background: #000000; padding: 0 1;
    }
    #cmd_input {
        dock: bottom; margin: 0 1; height: 3;
        border: solid #1a1a2e;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "", show=False),
        Binding("r", "refresh", "", show=False),
    ]

    def __init__(self, view_mode: str | None = None) -> None:
        super().__init__()
        self._spin: int = 0
        self._view_mode = (view_mode or ws.get_workflow_last_view_mode() or "chain").lower()

        # Session tracking
        self._seen_activity_min_ts: float | None = None
        self._last_active_step: str = ""
        self._shown_file_events: list[tuple[str, str]] = []
        self._token_warned: bool = False
        self._seen_running: bool = False

        # Inline mode flags
        self._post_delete_mode: bool = False
        self._exit_confirm_mode: bool = False
        self._last_task_text: str = ""
        self._attempt_count: int = 1

    # ── compose ──────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Static(id="hint")
        yield Static(id="pipeline_bar", expand=True)
        with VerticalScroll(id="scroll_area"):
            yield RichLog(
                id="stream_panel",
                highlight=False, markup=True, wrap=True, auto_scroll=False,
            )
            yield Static(id="live_step")
        yield Input(id="cmd_input", placeholder=_CMD_HINT)

    # ── lifecycle ────────────────────────────────────────────────────────

    def action_quit(self) -> None:
        snap = ws.get_pipeline_snapshot()
        if str(snap.get("active_step") or "idle") not in ("idle", "end_failed"):
            self._ask_exit_inline()
        else:
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

    def _scroll_end(self) -> None:
        try:
            self.query_one("#scroll_area", VerticalScroll).scroll_end(animate=False)
        except LookupError:
            pass

    # ── tick ─────────────────────────────────────────────────────────────

    def _tick_refresh(self) -> None:
        self._spin += 1
        snap = ws.get_pipeline_snapshot()
        active = str(snap.get("active_step") or "idle")
        if active not in ("idle", "end_failed", "") or snap.get("ambassador_status") == "running":
            self._seen_running = True
        if self._seen_running and snap.get("run_finished") and not snap.get("paused_at_gate"):
            self._flush_final_events()
            self.exit()
            return
        self._refresh_views()

    # ── render ───────────────────────────────────────────────────────────

    def _refresh_views(self) -> None:
        ws.prune_stale_pipeline_notifications()
        ws.apply_stale_workflow_ui_if_needed(_project_root_default())

        snap = ws.get_pipeline_snapshot()
        tier = snap["brief_tier"]
        last_node = ws.load_session().get("last_node")
        last_node_s = str(last_node) if last_node else None
        selected_leader = snap.get("brief_selected_leader") or ""
        now = time.time()
        toast = str(snap.get("toast") or "")
        buf = str(snap.get("leader_stream_buffer") or "")
        active = str(snap.get("active_step") or "idle")

        # ── activity min_ts reset ──
        mt = _activity_min_ts_kw() or 0.0
        if self._seen_activity_min_ts is None:
            self._seen_activity_min_ts = mt
        elif mt > self._seen_activity_min_ts + 1e-9:
            self._seen_activity_min_ts = mt
            self._last_active_step = ""
            self._shown_file_events = []
            self._token_warned = False

        pt, ct = _parse_token_counts()

        # ── pipeline bar (fixed chain, dots update live) ──
        steps = _steps_for_tier(tier)
        states = _compute_visual_states(steps, snap, last_node_s, now)
        pipe = _build_pipeline_markup(steps, states, tier, selected_leader, self._spin)
        sw = _event_sequence_warning()
        if sw:
            pipe += f"\n[yellow]{sw}[/yellow]"
        try:
            self.query_one("#pipeline_bar", Static).update(pipe)
        except LookupError:
            pass

        # ── token warning ──
        if (pt + ct) > TOKEN_WARN_THRESHOLD and not self._token_warned:
            self._token_warned = True
            self._slog().write(f"[bold yellow]⚠ Token budget: {pt+ct:,} / 262k[/bold yellow]")

        # ── hint bar ──
        sc = _SPINNER[self._spin % len(_SPINNER)]
        tok = f"  [dim]in:{pt:,} out:{ct:,}[/dim]" if (pt or ct) else ""
        hparts: list[str] = []
        if toast.strip():
            hparts.append(f"[bold #e0af68]{toast}[/bold #e0af68]  ")
        hparts.append(f"[bold #7aa2f7]chain[/bold #7aa2f7]  [yellow]{active}[/yellow]  Tier {tier or '—'}{tok}")
        try:
            self.query_one("#hint", Static).update("".join(hparts))
        except LookupError:
            pass

        # ── step transition → write completion to RichLog ──
        if active != self._last_active_step:
            self._on_step_transition(self._last_active_step, active, pt, ct)
            self._last_active_step = active

        # ── update live_step every tick ──
        self._render_live_step(active, buf, pt, ct)

        # ── file write events ──
        file_evs = _parse_file_events()
        new_evs = file_evs[len(self._shown_file_events):]
        if new_evs:
            for node, detail in new_evs:
                self._slog().write(f"[dim]    ✓ {detail}[/dim]")
            self._shown_file_events = file_evs

    def _on_step_transition(self, prev: str, active: str, pt: int, ct: int) -> None:
        """Write ONE green completion line to RichLog when step finishes."""
        slog = self._slog()

        if prev in _GEN_STEPS:
            role = _ROLE.get(prev, prev)
            action = _ACTION.get(prev, prev)
            tok = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
            slog.write("")
            slog.write(f"{action}  [bold green]●[/bold green]  [dim]({role})[/dim]{tok}")

        elif prev == "human_context_gate" and active not in ("human_context_gate",):
            slog.write("")
            slog.write(f"Review context.md  [bold green]●[/bold green]  [dim](accepted)[/dim]")

        if active in _GEN_STEPS or active in ("human_context_gate", "finalize_phase1"):
            slog.write("")  # blank separator; content will appear in live_step

    def _render_live_step(self, active: str, buf: str, pt: int, ct: int) -> None:
        """Replace #live_step every tick to animate spinner."""
        sc = _SPINNER[self._spin % len(_SPINNER)]

        try:
            live = self.query_one("#live_step", Static)
        except LookupError:
            return

        if active in ("idle", "", "end_failed"):
            live.update("")
            return

        if active in _GEN_STEPS:
            role = _ROLE.get(active, active)
            action = _ACTION.get(active, active)

            meta: list[str] = []
            if pt or ct:
                meta.append(f"token in: {pt:,}  token out: {ct:,}")
            meta.append(f"role: {role}")
            if self._attempt_count > 1:
                meta.append(f"attempts: {self._attempt_count}")
            meta_s = f"  [dim]({', '.join(meta)})[/dim]" if meta else ""

            buf_lines = [ln for ln in buf.split("\n") if ln.strip()] if buf else []
            last6 = buf_lines[-6:]

            lines: list[str] = [f"{action}{meta_s}  [#888888]{sc}[/#888888]"]
            if last6:
                lines.append(f"[dim]└── {last6[0][:100]}[/dim]")
                for ln in last6[1:]:
                    lines.append(f"[dim]    {ln[:100]}[/dim]")

            live.update("\n".join(lines))

        elif active == "human_context_gate":
            if self._post_delete_mode:
                task_hint = f" [bold]'{self._last_task_text[:40]}'[/bold]" if self._last_task_text else ""
                live.update(
                    f"Review context.md  [red]✗[/red]  [red]Rejected[/red]"
                    f" — Regenerate{task_hint}? [bold](y/n)[/bold]"
                )
            else:
                live.update(
                    f"Review context.md  [yellow]◉[/yellow]"
                    f"  [dim](accept · delete · check)[/dim]"
                )

        elif active == "finalize_phase1":
            live.update(f"[dim]Finalize pipeline…  {sc}[/dim]")

        else:
            live.update(f"[dim]{sc} {active}[/dim]")

        self._scroll_end()

    def _flush_final_events(self) -> None:
        slog = self._slog()
        pt, ct = _parse_token_counts()
        tok = f"  [dim](in:{pt:,} out:{ct:,})[/dim]" if (pt or ct) else ""
        file_evs = _parse_file_events()
        for node, detail in file_evs[len(self._shown_file_events):]:
            slog.write(f"[dim]    ✓ {detail}[/dim]")
        slog.write("")
        slog.write(f"[bold green]●[/bold green] Pipeline complete — {time.strftime('%H:%M:%S')}{tok}")
        try:
            self.query_one("#live_step", Static).update("")
        except LookupError:
            pass
        self._scroll_end()

    def _slog(self) -> RichLog:
        return self.query_one("#stream_panel", RichLog)

    # ── inline helpers ────────────────────────────────────────────────────

    def _ask_exit_inline(self) -> None:
        self._exit_confirm_mode = True
        self._slog().write("")
        self._slog().write(f"[bold yellow]⚠[/bold yellow] Workflow running — Exit & cleanup? [bold](y/n)[/bold]")
        try:
            self.query_one("#cmd_input", Input).placeholder = "y / n"
        except LookupError:
            pass
        self._scroll_end()

    def _do_cleanup_exit(self) -> None:
        self._slog().write(f"[dim]  Stopping pipeline…[/dim]")
        try:
            ws.request_pipeline_stop()
        except Exception:
            pass
        try:
            from core.cli.pythonCli.flows.context.monitor_actions import apply_context_delete_from_monitor
            apply_context_delete_from_monitor(_project_root_default())
        except Exception:
            pass
        ws.reset_pipeline_visual()
        self.exit()

    def _start_decline_countdown(self) -> None:
        self._slog().write(f"[dim]  Clearing in 3…[/dim]")
        self._scroll_end()

        def _run() -> None:
            for r in (2, 1, 0):
                time.sleep(1.0)
                self.call_from_thread(
                    lambda r=r: (self._slog().write(f"[dim]  Clearing in {r}…[/dim]"), self._scroll_end())
                )
            def _clear() -> None:
                try:
                    self._slog().clear()
                    self.query_one("#live_step", Static).update("")
                except LookupError:
                    pass
                self._last_active_step = ""
                self._shown_file_events = []
                ws.reset_pipeline_visual()
            self.call_from_thread(_clear)

        threading.Thread(target=_run, daemon=True).start()

    # ── commands ─────────────────────────────────────────────────────────

    @on(Input.Submitted, "#cmd_input")
    def _on_cmd(self, event: Input.Submitted) -> None:
        raw = (event.value or "").strip()
        event.input.value = ""
        self._focus_cmd()

        root = _project_root_default()
        slog = self._slog()

        if self._exit_confirm_mode:
            self._exit_confirm_mode = False
            try:
                self.query_one("#cmd_input", Input).placeholder = _CMD_HINT
            except LookupError:
                pass
            if raw.lower() in ("y", "yes"):
                self._do_cleanup_exit()
            else:
                slog.write(f"[dim]  Cancelled[/dim]")
                self._scroll_end()
            return

        if self._post_delete_mode:
            self._post_delete_mode = False
            try:
                self.query_one("#cmd_input", Input).placeholder = _CMD_HINT
            except LookupError:
                pass
            if not raw or raw.lower() in ("n", "no"):
                slog.write(f"[dim]  Skipped regeneration[/dim]")
                self._scroll_end()
                self._start_decline_countdown()
            elif raw.lower() in ("y", "yes"):
                self._attempt_count += 1
                slog.write(f"[cyan]  ↳ Regenerating…[/cyan]  [dim](attempt {self._attempt_count})[/dim]")
                ws.reset_pipeline_visual()
                ws.set_pipeline_run_finished(False)
                self._last_active_step = ""
                self._shown_file_events = []
                self._scroll_end()
                if self._last_task_text:
                    from core.cli.pythonCli.flows.start_flow import start_pipeline_from_tui
                    start_pipeline_from_tui(self._last_task_text, root, "agent")
                    self._seen_running = True
                else:
                    slog.write(f"[dim]  No previous task — use 'task <text>'[/dim]")
            else:
                self._do_new_task(raw, "agent", root, slog)
            return

        if not raw:
            return

        parts = raw.split(None, 1)
        cmd = parts[0].lower()
        rest = parts[1].strip() if len(parts) > 1 else ""

        log_system_action("monitor.input", raw[:300])

        if cmd in ("exit", "quit", "q", "back"):
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle", "end_failed", ""):
                self._ask_exit_inline()
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
                slog.write(f"[dim]✗ No pending gate[/dim]")
                self._scroll_end()
                return
            slog.write("")
            slog.write(f"Review context.md  [bold green]●[/bold green]  [dim]Accepting…[/dim]")
            self._scroll_end()

            def _accept_bg() -> None:
                try:
                    from core.cli.pythonCli.flows.context.monitor_actions import apply_context_accept_from_monitor
                    apply_context_accept_from_monitor(root)
                except Exception:
                    pass
            threading.Thread(target=_accept_bg, daemon=True).start()
            return

        if cmd == "delete":
            try:
                from core.cli.pythonCli.flows.context.monitor_actions import apply_context_delete_from_monitor
                apply_context_delete_from_monitor(root)
                ws.set_pipeline_paused_at_gate(False)
                ws.set_paused_for_review(False)
                slog.write("")
                slog.write(
                    f"Review context.md  [red]✗[/red]  [red]Rejected[/red]"
                    f"  [dim]{time.strftime('%H:%M:%S')}[/dim]"
                )
                self._post_delete_mode = True
                if self._last_task_text:
                    slog.write(f"[dim]  Regenerate [bold]'{self._last_task_text[:50]}'[/bold]? (y/n)[/dim]")
                else:
                    slog.write(f"[dim]  Regenerate? (y/n) or type new task[/dim]")
                try:
                    self.query_one("#cmd_input", Input).placeholder = "y / n / <new task>"
                except LookupError:
                    pass
                self._scroll_end()
            except Exception as e:
                slog.write(f"[red]✗ Delete failed: {e}[/red]")
                self._scroll_end()
            return

        if cmd == "task":
            if not rest:
                slog.write(f"[dim]✗ Usage: task <text> [ask|agent][/dim]")
                self._scroll_end()
                return
            snap = ws.get_pipeline_snapshot()
            if str(snap.get("active_step") or "idle") not in ("idle",):
                slog.write(f"[dim]✗ Pipeline running — wait or use 'btw <msg>'[/dim]")
                self._scroll_end()
                return
            task_parts = rest.rsplit(None, 1)
            if len(task_parts) == 2 and task_parts[1].lower() in ("ask", "agent"):
                task_text, task_mode = task_parts[0].strip(), task_parts[1].lower()
            else:
                task_text, task_mode = rest, "agent"
            self._do_new_task(task_text, task_mode, root, slog)
            return

        if cmd == "dismiss":
            nid = _match_notification_id(rest) or rest
            if nid:
                ws.dismiss_pipeline_notification(nid)
            else:
                slog.write(f"[dim]✗ Usage: dismiss <id>[/dim]")
                self._scroll_end()
            return

        if cmd == "view":
            nid = _match_notification_id(rest) or rest
            if not nid:
                slog.write(f"[dim]✗ Usage: view <id>[/dim]")
                self._scroll_end()
                return
            for n in ws.list_active_notifications():
                if str(n.get("id", "")).startswith(nid):
                    extra = n.get("extra") if isinstance(n.get("extra"), dict) else {}
                    p = str(extra.get("context_path") or extra.get("state_path") or "")
                    if p:
                        self.push_screen(ContextFilePreviewScreen(p))
                        self.set_timer(0.05, self._focus_cmd)
                        return
            slog.write(f"[dim]✗ Not found: {nid}[/dim]")
            self._scroll_end()
            return

        if cmd == "btw":
            snap = ws.get_pipeline_snapshot()
            active_s = str(snap.get("active_step") or "idle")
            slog.write("")
            slog.write(f"[dim]── btw {time.strftime('%H:%M:%S')}  {active_s}  Tier {snap.get('brief_tier') or '—'} ──[/dim]")
            self._scroll_end()
            if rest:
                if active_s not in ("idle",):
                    slog.write(f"[dim yellow]  pipeline active — note queued[/dim yellow]")
                def _run_btw(msg: str = rest, _snap: dict = snap) -> None:
                    try:
                        from agents.compact_worker import CompactWorker, build_state_summary_for_btw
                        result = CompactWorker().process_btw(msg, build_state_summary_for_btw(_snap))
                        self.call_from_thread(self._slog().write, f"[cyan]  ↳ {result[:300]}[/cyan]")
                        ws.enqueue_monitor_command("btw_note", {"note": result, "raw": msg})
                    except Exception as e:
                        self.call_from_thread(self._slog().write, f"[dim red]  btw error: {e}[/dim red]")
                threading.Thread(target=_run_btw, daemon=True).start()
            self._refresh_views()
            return

        slog.write(f"[dim]✗ '{cmd}' unknown  —  {_CMD_HINT}[/dim]")
        self._scroll_end()

    def _do_new_task(self, task_text: str, task_mode: str, root: str, slog: RichLog) -> None:
        self._last_task_text = task_text
        self._attempt_count = 1

        if task_mode == "agent":
            try:
                from core.cli.pythonCli.flows.start_flow import _looks_like_chat_intent
                from core.cli.pythonCli.flows.ask_flow import looks_like_code_intent
                if _looks_like_chat_intent(task_text) and not looks_like_code_intent(task_text):
                    slog.write("")
                    slog.write(f"[dim]  Question detected → ask mode[/dim]")
                    ws.enqueue_monitor_command("start_workflow", {"prompt": task_text, "mode": "ask", "project_root": root})
                    self.set_timer(0.3, self.exit)
                    return
            except Exception:
                pass

        slog.write("")
        slog.write(f"[bold cyan]●[/bold cyan] Task started [{task_mode}] — {time.strftime('%H:%M:%S')}")
        slog.write(Text(task_text[:200]))
        self._scroll_end()

        ws.reset_pipeline_visual()
        ws.set_pipeline_run_finished(False)
        self._last_active_step = ""
        self._shown_file_events = []
        from core.cli.pythonCli.flows.start_flow import start_pipeline_from_tui
        start_pipeline_from_tui(task_text, root, task_mode)
        self._seen_running = True
