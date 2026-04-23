from __future__ import annotations

from pathlib import Path
from typing import Any


def artifact_detail(path: str | Path, *, task_id: str = "", producer_node: str = "") -> dict[str, str]:
    p = Path(path)
    return {
        "task_id": task_id,
        "producer_node": producer_node,
        "filename": p.name,
        "path": str(p),
    }


def workflow_event(node: str, action: str, detail: Any = "", *, level: str = "info") -> None:
    from core.cli.workflow.runtime.activity_log import append_workflow_activity

    append_workflow_activity(node, action, detail, level=level)


def system_event(action: str, detail: str = "") -> None:
    from core.cli.state import log_system_action

    log_system_action(action, detail)


def log_state_json_written(path: str | Path, node: str = "ambassador") -> None:
    workflow_event(node, "state_json_written", artifact_detail(path, producer_node=node))


def log_state_json_deleted_on_accept(path: str | Path, node: str = "human_context_gate") -> None:
    workflow_event(node, "state_json_deleted_on_accept", artifact_detail(path, producer_node=node))


__all__ = [
    "workflow_event",
    "system_event",
    "artifact_detail",
    "log_state_json_written",
    "log_state_json_deleted_on_accept",
]
