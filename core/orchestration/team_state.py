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
    setup_commands: list[str]
    validation_commands: list[str]
    worker_assignments: dict[str, dict[str, Any]]
    worker_key: str
    worker_a_result: Optional[dict]
    worker_b_result: Optional[dict]
    worker_c_result: Optional[dict]
    worker_d_result: Optional[dict]
    worker_e_result: Optional[dict]
    worker_result: Optional[dict]
    worker_results: dict[str, dict]
    setup_result: Optional[dict]
    secretary_result: Optional[dict]
    restore_result: Optional[dict]


__all__ = ["TeamState"]

