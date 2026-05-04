from __future__ import annotations

from typing import Any, Optional, TypedDict


class TeamState(TypedDict, total=False):
    task: str
    project_root: str
    original_prompt: str
    brief_dict: dict[str, Any]
    context_path: Optional[str]
    validation_status: Optional[str]
    state_json_path: Optional[str]
    leader_failed: bool
    tools_path: Optional[str]
    curator_failed: bool


__all__ = ["TeamState"]

