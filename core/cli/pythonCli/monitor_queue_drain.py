"""Drain workflow monitor JSON queue (session file) from main CLI loop."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.cli.pythonCli.flows.context_flow import (
    apply_context_accept_from_monitor,
    apply_context_back_from_monitor,
    apply_context_delete_from_monitor,
    apply_context_prepare_regenerate,
)
from core.cli.pythonCli.monitor_payload import resolve_trusted_project_root, sanitize_monitor_prompt
from core.cli.pythonCli.state import log_system_action
from core.cli.pythonCli.chrome.ui import console
from core.cli.pythonCli.nav import NavToMain
from core.cli.pythonCli.workflow.runtime import session as ws
from core.cli.pythonCli.workflow.runtime.runner import rewind_to_checkpoint, rewind_to_last_gate
from core.config import config

_ALLOWED_ACTIONS = frozenset(
    {
        "rewind_gate",
        "rewind_checkpoint",
        "regenerate",
        "start_workflow",
        "context_accept",
        "context_back",
        "context_delete",
        "context_regenerate",
    }
)


def drain_monitor_command_queue(repo_root: str, run_start_entry: Callable[..., Any]) -> None:
    for c in ws.drain_monitor_command_queue():
        act = c.get("action")
        if act not in _ALLOWED_ACTIONS:
            log_system_action("monitor.drain.ignored", f"unknown_action={str(act)[:80]}")
            continue
        pl = c.get("payload") if isinstance(c.get("payload"), dict) else {}
        pl = pl or {}
        trusted = resolve_trusted_project_root(
            (pl.get("project_root") or "").strip() or None,
            repo_root=repo_root,
            home_config_dir=config.BASE_DIR,
        )
        if trusted is None:
            log_system_action("monitor.drain.rejected", f"action={act} bad_project_root={str(pl.get('project_root'))[:120]}")
            console.print("[yellow]Monitor queue: project_root không hợp lệ — bỏ qua lệnh.[/yellow]")
            continue
        root = str(trusted)
        log_system_action("monitor.drain", str(act))

        if act == "rewind_gate":
            ok = rewind_to_last_gate()
            console.print("[green]Đã rewind về gate gần nhất.[/green]" if ok else "[yellow]Rewind gate thất bại.[/yellow]")
        elif act == "rewind_checkpoint":
            target_raw = pl.get("target")
            if isinstance(target_raw, bool) or target_raw is None:
                console.print("[yellow]rewind_checkpoint: target không hợp lệ.[/yellow]")
                continue
            if isinstance(target_raw, int):
                target_ck: int | str = target_raw
            elif isinstance(target_raw, str) and target_raw.strip():
                target_ck = target_raw.strip()
            else:
                console.print("[yellow]rewind_checkpoint: target không hợp lệ.[/yellow]")
                continue
            ok = rewind_to_checkpoint(target_ck)
            console.print(
                f"[green]Đã rewind checkpoint {target_ck}.[/green]"
                if ok
                else f"[yellow]Rewind checkpoint {target_ck} thất bại.[/yellow]"
            )
        elif act == "regenerate":
            p = sanitize_monitor_prompt(pl.get("prompt"))
            if not p:
                console.print("[yellow]Regenerate (monitor): thiếu prompt — bỏ qua. Nhập đầy đủ trong monitor.[/yellow]")
            else:
                from core.cli.pythonCli.workflow.runtime.activity_log import clear_workflow_activity_log

                clear_workflow_activity_log()
                try:
                    run_start_entry(p, regenerate_prelude=p[:400])
                except NavToMain:
                    pass
        elif act == "start_workflow":
            p = sanitize_monitor_prompt(pl.get("prompt"))
            mode = str(pl.get("mode") or "agent").lower()
            if mode not in ("ask", "agent"):
                mode = "agent"
            if p:
                try:
                    run_start_entry(p, force_mode=mode)
                except NavToMain:
                    pass
            else:
                console.print("[yellow]start_workflow: thiếu prompt.[/yellow]")
        elif act == "context_accept":
            if apply_context_accept_from_monitor(root):
                console.print("[green]Đã accept context.md và resume (monitor).[/green]")
            else:
                console.print("[yellow]context_accept: không áp dụng được (thiếu file / gate).[/yellow]")
        elif act == "context_back":
            apply_context_back_from_monitor(root)
            console.print("[dim]Đã back từ review (monitor) — giữ pause gate, chưa resume.[/dim]")
        elif act == "context_delete":
            if apply_context_delete_from_monitor(root):
                console.print("[yellow]Đã xóa context (monitor). Có thể start/regenerate mới.[/yellow]")
            else:
                console.print("[dim]context_delete: không có context.[/dim]")
        elif act == "context_regenerate":
            apply_context_prepare_regenerate(root)
            p = sanitize_monitor_prompt(pl.get("prompt"))
            if p:
                from core.cli.pythonCli.workflow.runtime.activity_log import clear_workflow_activity_log

                clear_workflow_activity_log()
                try:
                    run_start_entry(p, regenerate_prelude=p[:400])
                except NavToMain:
                    pass
            else:
                console.print("[yellow]context_regenerate: thiếu prompt sau khi xóa context.[/yellow]")


__all__ = ["drain_monitor_command_queue"]
