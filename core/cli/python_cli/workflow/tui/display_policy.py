from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class WorkflowDisplayPolicy:
    view_mode: str
    use_chain: bool


def resolve_display_policy(settings: dict) -> WorkflowDisplayPolicy:
    view_mode = str(settings.get("workflow_view_mode") or "chain").lower()
    view_mode = "list" if view_mode == "list" else "chain"
    return WorkflowDisplayPolicy(
        view_mode=view_mode,
        use_chain=view_mode == "chain",
    )


__all__ = ["WorkflowDisplayPolicy", "resolve_display_policy"]
