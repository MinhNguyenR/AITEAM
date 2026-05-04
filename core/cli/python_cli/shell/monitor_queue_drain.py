"""Drain workflow monitor JSON queue (session file) from main CLI loop."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from core.cli.python_cli.features.context.flow import (
    apply_context_accept_from_monitor,
    apply_context_back_from_monitor,
    apply_context_delete_from_monitor,
    apply_context_prepare_regenerate,
)
from core.cli.python_cli.shell.monitor_payload import resolve_trusted_project_root, sanitize_monitor_prompt
from core.app_state import log_system_action
from core.cli.python_cli.ui.ui import console
from core.cli.python_cli.shell.nav import NavToMain
from core.runtime import session as ws
from core.cli.python_cli.workflow.runtime.graph.runner import rewind_to_checkpoint, rewind_to_last_gate
from core.config import config
from core.cli.python_cli.i18n import t

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
            console.print(f"[yellow]{t('monitor.bad_root')}[/yellow]")
            continue
        root = str(trusted)
        log_system_action("monitor.drain", str(act))

        if act == "rewind_gate":
            ok = rewind_to_last_gate()
            msg = t('monitor.rewind_ok') if ok else t('monitor.rewind_fail')
            console.print(f"[{'green' if ok else 'yellow'}]{msg}[/]")
        elif act == "rewind_checkpoint":
            target_raw = pl.get("target")
            if isinstance(target_raw, bool) or target_raw is None:
                console.print(f"[yellow]{t('monitor.checkpoint_invalid')}[/yellow]")
                continue
            if isinstance(target_raw, int):
                target_ck: int | str = target_raw
            elif isinstance(target_raw, str) and target_raw.strip():
                target_ck = target_raw.strip()
            else:
                console.print(f"[yellow]{t('monitor.checkpoint_invalid')}[/yellow]")
                continue
            ok = rewind_to_checkpoint(target_ck)
            msg = t('monitor.checkpoint_ok').format(ck=target_ck) if ok else t('monitor.checkpoint_fail').format(ck=target_ck)
            console.print(f"[{'green' if ok else 'yellow'}]{msg}[/]")
        elif act == "regenerate":
            p = sanitize_monitor_prompt(pl.get("prompt"))
            if not p:
                console.print(f"[yellow]{t('monitor.regen_missing_prompt')}[/yellow]")
            else:
                from core.cli.python_cli.workflow.runtime.persist.activity_log import clear_workflow_activity_log

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
                console.print(f"[yellow]{t('monitor.start_missing_prompt')}[/yellow]")
        elif act == "context_accept":
            if apply_context_accept_from_monitor(root):
                console.print(f"[green]{t('monitor.accept_ok')}[/green]")
            else:
                console.print(f"[yellow]{t('monitor.accept_fail')}[/yellow]")
        elif act == "context_back":
            apply_context_back_from_monitor(root)
            console.print(f"[dim]{t('monitor.back_msg')}[/dim]")
        elif act == "context_delete":
            if apply_context_delete_from_monitor(root):
                console.print(f"[yellow]{t('monitor.delete_ok')}[/yellow]")
            else:
                console.print(f"[dim]{t('monitor.delete_no_context')}[/dim]")
        elif act == "context_regenerate":
            apply_context_prepare_regenerate(root)
            p = sanitize_monitor_prompt(pl.get("prompt"))
            if p:
                from core.cli.python_cli.workflow.runtime.persist.activity_log import clear_workflow_activity_log

                clear_workflow_activity_log()
                try:
                    run_start_entry(p, regenerate_prelude=p[:400])
                except NavToMain:
                    pass
            else:
                console.print(f"[yellow]{t('monitor.regen_missing_prompt_post_delete')}[/yellow]")


__all__ = ["drain_monitor_command_queue"]
