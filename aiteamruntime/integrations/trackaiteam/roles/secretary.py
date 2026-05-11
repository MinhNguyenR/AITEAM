from __future__ import annotations

from concurrent.futures import TimeoutError as FutureTimeoutError
import time
from typing import Any

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext


def secretary_agent(ctx: AgentContext, event: AgentEvent) -> None:
    """Route every command through the shared Secretary subprocess."""
    command = str(event.payload.get("command") or "")
    requested_cwd = str(event.payload.get("cwd") or ".")
    workspace = ctx.runtime.resources.workspace_for(ctx.run_id)
    cwd = workspace if requested_cwd in {"", "."} and workspace else requested_cwd
    argv = event.payload.get("argv")
    timeout = float(event.payload.get("timeout") or 20.0)
    stage = "setup" if event.kind == "setup_requested" else str(event.stage or event.payload.get("stage") or "validate")
    if event.kind == "setup_requested":
        result_kind = "setup_done"
    elif event.kind == "secretary_command":
        result_kind = "secretary_result"
    else:
        result_kind = "terminal_result"

    if not isinstance(argv, list) or not argv:
        ctx.emit(
            result_kind,
            {"command": command, "cwd": cwd, "status": "failed", "exit_code": 2,
             "output": "argv required", "stdout": "", "stderr": "argv required"},
            status="error",
            stage=stage,
            role_state="done",
        )
        ctx.emit("done", {"stage": stage, "command": command}, stage=stage)
        return

    started = time.monotonic()
    ctx.emit(
        "terminal_running",
        {"command": command, "cwd": cwd, "status": "running"},
        status="running",
        stage=stage,
        role_state="running",
    )
    try:
        result = run_secretary_command_with_retry(ctx, [str(part) for part in argv], cwd=cwd or ".", timeout=timeout)
    except Exception as exc:
        message = f"secretary error ({type(exc).__name__}): {exc or 'no result returned before wait deadline'}"
        result = {
            "exit_code": 1,
            "stdout": "",
            "stderr": message,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timed_out": isinstance(exc, FutureTimeoutError),
        }

    exit_code = int(result.get("exit_code") or 0)
    output = "\n".join(p for p in (result.get("stdout") or "", result.get("stderr") or "") if p).strip()
    status = "passed" if exit_code == 0 else ("timeout" if result.get("timed_out") else "failed")
    ctx.emit(
        result_kind,
        {
            "command": command,
            "cwd": cwd,
            "status": status,
            "exit_code": exit_code,
            "output": output,
            "stdout": result.get("stdout") or "",
            "stderr": result.get("stderr") or "",
            "timed_out": bool(result.get("timed_out")),
            "gate_id": event.payload.get("gate_id") or "",
            "setup_index": event.payload.get("setup_index"),
            "setup_total": event.payload.get("setup_total"),
            "creates": list(event.payload.get("creates") or []),
            "work_item_id": event.work_item_id or event.payload.get("work_item_id") or "",
        },
        status="ok" if exit_code == 0 else ("timeout" if result.get("timed_out") else "error"),
        stage=stage,
        work_item_id=event.work_item_id or str(event.payload.get("work_item_id") or ""),
        duration_ms=int(result.get("duration_ms") or (time.monotonic() - started) * 1000),
        role_state="done",
    )
    if stage == "validate" and exit_code == 0:
        ctx.emit(
            "validated",
            {"stage": "validate", "command": command, "result": "passed", "work_item_id": event.work_item_id or event.payload.get("work_item_id") or ""},
            stage="validate",
            work_item_id=event.work_item_id or str(event.payload.get("work_item_id") or ""),
            role_state="done",
        )
    ctx.emit(
        "done",
        {"stage": stage, "command": command, "work_item_id": event.work_item_id or event.payload.get("work_item_id") or ""},
        stage=stage,
        work_item_id=event.work_item_id or str(event.payload.get("work_item_id") or ""),
    )


def run_secretary_command_with_retry(ctx: AgentContext, argv: list[str], *, cwd: str, timeout: float) -> dict[str, Any]:
    secretary = ctx.runtime.secretary()
    future = secretary.submit(argv, cwd=cwd, timeout=timeout)
    try:
        return future.result(timeout=timeout + 5.0)
    except FutureTimeoutError:
        try:
            secretary.terminate(timeout=1.0)
        except Exception:
            pass
        ctx.runtime._secretary = None
        retry = ctx.runtime.secretary().submit(argv, cwd=cwd, timeout=timeout)
        return retry.result(timeout=timeout + 5.0)
