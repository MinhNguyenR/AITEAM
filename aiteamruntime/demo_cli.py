from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from .agents import DEFAULT_AGENT_LANES
from .core.events import AgentEvent
from .core.runtime import AgentContext, AgentRuntime, AgentSpec

SECRET = "nha5pa"

STATE_LABELS = {
    "blocked": ("Blocked", "Blocked", "red"),
    "classifying": ("Classifying", "Classified", "cyan"),
    "reading": ("Reading", "Read", "blue"),
    "reasoning": ("Reasoning", "Reasoned", "magenta"),
    "writing": ("Writing", "Wrote", "yellow"),
    "terminal_requested": ("Requesting terminal", "Requested terminal", "yellow"),
    "terminal_running": ("Running terminal", "Ran terminal", "yellow"),
    "terminal_result": ("Collecting result", "Collected result", "green"),
    "file_update": ("Updating file", "Updated file", "green"),
    "file_create": ("Creating file", "Created file", "green"),
    "question": ("Asking", "Asked", "cyan"),
    "done": ("Finishing", "Done", "green"),
    "error": ("Failing", "Failed", "red"),
    "abort": ("Aborting", "Aborted", "red"),
}


@dataclass
class RoleState:
    label: str = "Idle"
    style: str = "dim"
    status_text: str = "idle"
    detail: str = ""
    updated_at: float = field(default_factory=time.time)


def _event_detail(event: AgentEvent) -> str:
    payload = event.payload or {}
    if event.kind in {"terminal_requested", "terminal_running", "terminal_result"}:
        command = str(payload.get("command") or "")
        output = str(payload.get("output") or "").strip()
        if event.kind == "terminal_result":
            exit_code = payload.get("exit_code", "")
            return f"Ran {command} -> exit {exit_code}" + (f" | {output[:60]}" if output else " | no output")
        return command
    if event.kind in {"file_update", "file_create", "writing", "reading"}:
        return str(payload.get("path") or payload.get("file") or payload.get("files") or "")
    if event.kind == "reasoning":
        return str(payload.get("content") or "")[:90]
    if event.kind == "blocked":
        return str(payload.get("reason") or payload.get("resource_key") or "")
    return str(payload.get("stage") or payload.get("summary") or payload.get("reason") or "")[:90]


def _terminal_block(event: AgentEvent) -> Text:
    payload = event.payload or {}
    command = str(payload.get("command") or "")
    output = str(payload.get("output") or "").strip()
    exit_code = payload.get("exit_code", "")
    style = "green" if event.kind == "terminal_result" and int(exit_code or 0) == 0 and output else "red"
    if event.kind == "terminal_running":
        style = "yellow"
    block = Text(style=style)
    label = "Ran" if event.kind == "terminal_result" else "Running"
    block.append(f"* {label} {command}\n", style=style)
    if output:
        lines = output.splitlines()
        for line in lines[:4]:
            block.append(f"  | {line[:92]}\n", style=style)
        if len(lines) > 4:
            block.append(f"  | ... +{len(lines) - 4} lines\n", style=style)
    elif event.kind == "terminal_result":
        block.append(f"  `- exit {exit_code}; no output\n", style="red")
    else:
        block.append("  `- running\n", style=style)
    return block


def _state_for(event: AgentEvent, latest: bool) -> tuple[str, str, str]:
    current, past, color = STATE_LABELS.get(event.kind, (event.kind, event.kind, "white"))
    label = current if latest and event.kind not in {"done", "terminal_result", "file_update", "file_create", "blocked", "error", "abort"} else past
    status = "running" if latest and label == current else str(event.status or "ok")
    if event.kind == "terminal_result":
        status = "ok" if int((event.payload or {}).get("exit_code") or 0) == 0 and str((event.payload or {}).get("output") or "").strip() else "error"
        color = "green" if status == "ok" else "red"
    return label, status, color


def _render(states: dict[str, RoleState], events: list[AgentEvent], done: bool, task: str) -> Panel:
    table = Table.grid(expand=True)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    table.add_column(ratio=1)
    rows = []
    for role in ("runtime", *DEFAULT_AGENT_LANES):
        state = states.get(role, RoleState())
        body = Text()
        body.append(role + "\n", style="bold white")
        body.append(state.label + " ", style=state.style)
        body.append(f"({state.status_text})\n", style="dim")
        if state.detail:
            body.append(state.detail[:110], style="dim")
        rows.append(Panel(body, border_style=state.style))
    for idx in range(0, len(rows), 3):
        table.add_row(*rows[idx : idx + 3])

    recent = Table.grid(expand=True)
    recent.add_column()
    recent.add_row(Text("Recent events", style="bold"))
    for event in events[-8:]:
        if event.kind in {"terminal_running", "terminal_result"}:
            recent.add_row(_terminal_block(event))
        else:
            label, status, color = _state_for(event, latest=False)
            recent.add_row(Text(f"#{event.sequence} {event.agent_id}: {label} - {_event_detail(event)}", style=color))
    task_text = task[:220] + ("..." if len(task) > 220 else "")
    table.add_row(
        Panel(recent, border_style="dim"),
        Panel(f"Run state: {'done' if done else 'running'}\nTask: {task_text}", border_style="green" if done else "yellow"),
        Panel("Standalone agent_runtime demo\nMain workflow is untouched.", border_style="blue"),
    )
    return Panel(table, title="aitest nha5pa", border_style="cyan")


def _runtime_start(event: AgentEvent) -> bool:
    return event.agent_id == "runtime" and event.kind == "classifying"


def _done_from(agent_id: str, stage: str):
    return lambda event: event.agent_id == agent_id and event.kind == "done" and str(event.payload.get("stage") or "") == stage


def _task_from_event(event: AgentEvent) -> str:
    return str((event.payload or {}).get("prompt") or (event.payload or {}).get("task") or "")


def _register_task_pipeline(runtime: AgentRuntime, task: str) -> AgentRuntime:
    def ambassador(ctx: AgentContext, event: AgentEvent) -> None:
        current_task = _task_from_event(event) or task
        ctx.emit("classifying", {"summary": current_task[:160], "tier": "DEMO"})
        time.sleep(0.15)
        ctx.emit("done", {"stage": "ambassador", "task": current_task, "selected_leader": "Leader"})

    def leader(ctx: AgentContext, event: AgentEvent) -> None:
        current_task = str(event.payload.get("task") or task)
        ctx.emit("reading", {"file": "task input", "purpose": "understand requested demo workflow"})
        time.sleep(0.15)
        ctx.emit("reasoning", {"content": f"Plan a safe standalone pipeline for: {current_task[:120]}"})
        time.sleep(0.15)
        ctx.emit("writing", {"file": "runtime plan", "content": "Assign Worker A and request Secretary validation."})
        ctx.emit("done", {"stage": "leader", "task": current_task, "assignment": "Worker A performs demo work and asks Secretary to validate."})

    def tool_curator(ctx: AgentContext, event: AgentEvent) -> None:
        ctx.emit("reading", {"file": "runtime plan", "purpose": "choose demo-safe tools"})
        time.sleep(0.1)
        ctx.emit("writing", {"file": "tool list", "tools": ["python subprocess", "agent_runtime trace bus"]})
        ctx.emit("done", {"stage": "tool_curator"})

    def worker(ctx: AgentContext, event: AgentEvent) -> None:
        current_task = str(event.payload.get("task") or task)
        ctx.emit("reading", {"files": ["aiteamruntime/runtime.py", "aiteamruntime/demo_cli.py"]})
        time.sleep(0.15)
        ctx.emit("reasoning", {"content": "Use a generated safe command so Secretary executes a real terminal step."})
        time.sleep(0.15)
        ctx.emit("writing", {"file": "demo task", "content": current_task[:180]})
        ctx.emit("file_update", {"path": "virtual/demo_task.txt", "added_lines": 3, "removed_lines": 0})
        safe_task = current_task.replace("\r", " ").replace("\n", " ")[:140]
        code = (
            "print('aitest pipeline ok')\n"
            f"print('task: {safe_task}')\n"
            "print('secretary terminal executed')\n"
        )
        command = "python -c \"print('aitest pipeline ok'); print('task: ...'); print('secretary terminal executed')\""
        ctx.request_terminal(command, cwd=".", payload={"argv": [sys.executable, "-c", code]})
        ctx.emit("done", {"stage": "worker", "task": current_task})

    def secretary(ctx: AgentContext, event: AgentEvent) -> None:
        payload = event.payload or {}
        command = str(payload.get("command") or "")
        cwd = str(payload.get("cwd") or ".")
        argv = payload.get("argv")
        ctx.emit("terminal_running", {"command": command, "cwd": cwd, "status": "running"})
        if not isinstance(argv, list) or not argv:
            ctx.emit("terminal_result", {"command": command, "cwd": cwd, "exit_code": 2, "output": "", "error": "missing argv"}, status="error")
            ctx.emit("done", {"stage": "secretary", "command": command})
            return
        try:
            result = subprocess.run(
                [str(part) for part in argv],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            output = (result.stdout or "") + (result.stderr or "")
            ctx.emit(
                "terminal_result",
                {
                    "command": command,
                    "cwd": cwd,
                    "status": "passed" if result.returncode == 0 else "failed",
                    "exit_code": result.returncode,
                    "output": output.strip(),
                },
                status="ok" if result.returncode == 0 else "error",
            )
        except Exception as exc:
            ctx.emit("terminal_result", {"command": command, "cwd": cwd, "exit_code": 1, "output": "", "error": str(exc)}, status="error")
        ctx.emit("done", {"stage": "secretary", "command": command})

    runtime.register(AgentSpec("Ambassador", ambassador, _runtime_start, lane="Ambassador"))
    runtime.register(AgentSpec("Leader", leader, _done_from("Ambassador", "ambassador"), lane="Leader"))
    runtime.register(AgentSpec("Tool Curator", tool_curator, _done_from("Leader", "leader"), lane="Tool Curator"))
    runtime.register(AgentSpec("Worker A", worker, _done_from("Leader", "leader"), lane="Worker A"))
    runtime.register(AgentSpec("Secretary", secretary, lambda event: event.kind == "terminal_requested", lane="Secretary"))
    return runtime


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aitest", description="Run the standalone agent_runtime workflow demo.")
    parser.add_argument("secret", nargs="?")
    parser.add_argument("--task", default="", help="Task text to feed into the demo pipeline.")
    parser.add_argument("--once", action="store_true", help="Render once after the run completes.")
    args = parser.parse_args(argv)
    if args.secret != SECRET:
        Console().print("[red]Usage: aitest nha5pa[/red]")
        return 2

    console = Console()
    task = str(args.task or "").strip()
    if not task:
        if args.once or not console.is_interactive:
            task = "Show how the standalone agent_runtime workflow processes a task."
        else:
            task = Prompt.ask("[cyan]Task for aitest pipeline[/cyan]", default="Show agent_runtime terminal flow")

    runtime = AgentRuntime()
    _register_task_pipeline(runtime, task)
    sub = runtime.bus.subscribe(replay=True, max_queue=2000)
    states: dict[str, RoleState] = {}
    events: list[AgentEvent] = []
    done = {"value": False}

    def _run() -> None:
        handle = runtime.start_run(run_id="aitest-demo", prompt=task, metadata={"source": "aitest"})
        handle.wait(timeout=10)
        runtime.emit("aitest-demo", "runtime", "done", {"stage": "runtime"})
        done["value"] = True
        runtime.shutdown()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    def _drain() -> None:
        while True:
            event = sub.get(timeout=0.01)
            if event is None:
                break
            events.append(event)
            label, status, color = _state_for(event, latest=True)
            states[event.agent_id] = RoleState(label=label, style=color, status_text=status, detail=_event_detail(event))

    if args.once:
        thread.join(timeout=12)
        _drain()
        console.print(_render(states, events, done["value"], task))
    else:
        with Live(_render(states, events, False, task), console=console, refresh_per_second=8, transient=False) as live:
            while thread.is_alive() or not done["value"]:
                _drain()
                live.update(_render(states, events, done["value"], task))
                time.sleep(0.08)
            _drain()
            live.update(_render(states, events, True, task))
    sub.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
