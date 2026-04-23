"""Shared state.json + leader context generation for LangGraph (no core.cli import on quiet path)."""

from __future__ import annotations

import json
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING

from core.config import config
from core.domain.routing_map import pipeline_registry_key_for_tier
from core.domain.delta_brief import build_state_payload
from utils.file_manager import atomic_write_text, paths_for_task
from utils.logger import log_state_json_written, workflow_event

if TYPE_CHECKING:
    from agents.ambassador import DeltaBrief


def write_task_state_json(
    brief: DeltaBrief,
    prompt: str,
    project_root: str,
    *,
    source_node: str = "ambassador",
) -> Path:
    _ = project_root
    task_paths = paths_for_task(brief.task_uuid)
    state_path = task_paths.state_path
    state_data = build_state_payload(brief, prompt, config.get_system_info()["hardware"])
    atomic_write_text(state_path, json.dumps(state_data, indent=2, ensure_ascii=False), encoding="utf-8")
    log_state_json_written(state_path, node=source_node)
    if source_node in ("ambassador", "leader_generate", "expert_solo"):
        try:
            from core.cli.workflow.runtime import session as ws

            ws.push_pipeline_notification(
                "state.json đã tạo",
                str(state_path),
                "state_json_ready",
                {"state_path": str(state_path)},
            )
        except (ImportError, RuntimeError, ValueError, TypeError):
            pass
    return state_path


def leader_generate_context(
    brief: DeltaBrief,
    prompt: str,
    project_root: str,
    *,
    quiet: bool = False,
    stream_to_monitor: bool = False,
) -> Path | None:
    from agents.expert import Expert
    from agents.leader import BaseLeader, LeaderHigh, LeaderLow, LeaderMed

    _by_key = {
        "LEADER_LOW": LeaderLow,
        "LEADER_MEDIUM": LeaderMed,
        "EXPERT": Expert,
        "LEADER_HIGH": LeaderHigh,
    }
    registry_key = pipeline_registry_key_for_tier(brief.tier)
    leader_class = _by_key.get(registry_key, LeaderMed)
    leader = leader_class(budget_limit_usd=5.0)
    cfg = config.get_worker(registry_key) or {}
    if not quiet:
        from rich.box import ROUNDED
        from rich.panel import Panel

        from core.cli.chrome.ui import PASTEL_BLUE, PASTEL_CYAN, PASTEL_LAVENDER, console

        console.print(
            Panel(
                f"[bold {PASTEL_CYAN}]🤖 {registry_key}[/bold {PASTEL_CYAN}]  [dim]{cfg.get('role', 'Leader')}[/dim]\n"
                f"[{PASTEL_LAVENDER}]Model: {cfg.get('model', leader.model_name)}[/{PASTEL_LAVENDER}]",
                border_style=PASTEL_BLUE,
                padding=(0, 2),
                box=ROUNDED,
            )
        )
    task_paths = paths_for_task(brief.task_uuid)
    state_path = task_paths.state_path
    if not state_path.exists():
        state_path = write_task_state_json(brief, prompt, project_root, source_node="leader_generate")
    if not quiet:
        from core.cli.chrome.ui import console

        console.print(f"[dim]📁 state.json → {state_path}[/dim]")
    if not quiet:
        from core.cli.chrome.ui import PASTEL_BLUE, console

        ctx_cm = console.status(f"[{PASTEL_BLUE}]⏳ {leader.agent_name} đang viết context.md...[/{PASTEL_BLUE}]")
    else:
        ctx_cm = nullcontext()
    with ctx_cm:
        ctx_path_str = leader.generate_context(str(state_path), stream_to_monitor=stream_to_monitor)
    ctx_path = Path(ctx_path_str)
    if BaseLeader.is_no_context(ctx_path):
        return None
    if not quiet:
        from core.cli.chrome.ui import PASTEL_CYAN, console

        console.print(f"[bold green]✅ context.md xong![/bold green]  [{PASTEL_CYAN}]{ctx_path}[/{PASTEL_CYAN}]")
    workflow_event("leader_generate", "context_written", str(ctx_path))
    return ctx_path


__all__ = ["write_task_state_json", "leader_generate_context"]
