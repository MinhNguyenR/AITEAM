from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDisplayPolicy:
    view_mode: str
    use_chain: bool


def resolve_display_policy(settings: dict) -> WorkflowDisplayPolicy:
    mode = str((settings or {}).get("workflow_view_mode") or "chain").strip().lower()
    if mode not in ("chain", "list"):
        mode = "chain"
    return WorkflowDisplayPolicy(view_mode=mode, use_chain=(mode == "chain"))


__all__ = ["WorkflowDisplayPolicy", "resolve_display_policy"]
