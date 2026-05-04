"""Pure orchestration services for workflow artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from core.config import config
from core.domain.delta_brief import build_state_payload
from core.domain.routing_map import pipeline_registry_key_for_tier
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
    if source_node in ("ambassador", "leader_generate"):
        try:
            from core.runtime import session as ws

            ws.push_pipeline_notification(
                "state.json da tao",
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
    from agents.leader import BaseLeader, LeaderHigh, LeaderLow, LeaderMed

    _ = quiet
    by_key = {
        "LEADER_LOW": LeaderLow,
        "LEADER_MEDIUM": LeaderMed,
        "LEADER_HIGH": LeaderHigh,
    }
    registry_key = pipeline_registry_key_for_tier(brief.tier)
    leader_class = by_key.get(registry_key, LeaderMed)
    leader = leader_class(budget_limit_usd=5.0)
    state_path = paths_for_task(brief.task_uuid).state_path
    if not state_path.exists():
        state_path = write_task_state_json(brief, prompt, project_root, source_node="leader_generate")
    ctx_path = Path(leader.generate_context(str(state_path), stream_to_monitor=stream_to_monitor))
    if BaseLeader.is_no_context(ctx_path):
        return None
    workflow_event("leader_generate", "context_written", str(ctx_path))
    return ctx_path


def tool_curator_generate_tools(
    context_path: str | Path,
    *,
    quiet: bool = True,
) -> Path | None:
    from agents.tool_curator import ToolCurator

    _ = quiet
    ctx = Path(context_path)
    if not ctx.exists():
        return None
    curator = ToolCurator(budget_limit_usd=2.0)
    try:
        tools_path = curator.generate_tools(str(ctx))
    except (OSError, ValueError, RuntimeError, TypeError, KeyError):
        workflow_event("tool_curator", "tool_curator_failed", "generate_tools raised")
        return None
    workflow_event("tool_curator", "tools_written", str(tools_path))
    return Path(tools_path)


__all__ = [
    "write_task_state_json",
    "leader_generate_context",
    "tool_curator_generate_tools",
]
