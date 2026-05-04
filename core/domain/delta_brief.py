from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

STATE_FILENAME = "state.json"
CONTEXT_FILENAME = "context.md"
VALIDATION_REPORT_FILENAME = "validation_report.md"
NO_CONTEXT_HEADER = "# NO_CONTEXT"


class DeltaBrief(BaseModel):
    task_uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    original_prompt: str
    summary: str
    tier: str
    target_model: str
    selected_leader: str
    intent: str = "agent"
    is_cuda_required: bool = False
    estimated_vram_usage: Optional[str] = None
    is_hardware_bound: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)
    language_detected: str = "unknown"
    complexity_score: float = Field(default=0.0, ge=0.0, le=1.0)

    @field_validator("tier")
    @classmethod
    def validate_tier(cls, v: str) -> str:
        allowed = {"LOW", "MEDIUM", "HARD"}
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Tier must be one of {allowed}, got '{v}'")
        return v_upper

    @field_validator("selected_leader")
    @classmethod
    def validate_leader(cls, v: str) -> str:
        allowed = {"LEADER_LOW", "LEADER_MEDIUM", "LEADER_HIGH"}
        if v not in allowed:
            raise ValueError(f"selected_leader must be one of {allowed}, got '{v}'")
        return v


def build_state_payload(brief: DeltaBrief, prompt: str, hardware_info: dict[str, Any]) -> dict[str, Any]:
    state_data: dict[str, Any] = {
        "task_uuid": brief.task_uuid,
        "original_prompt": prompt,
        "tier": brief.tier,
        "language": brief.language_detected,
        "complexity": brief.complexity_score,
        "is_cuda": brief.is_cuda_required,
        "constraints": [],
        "hardware": hardware_info,
    }
    if brief.is_cuda_required:
        state_data["constraints"].append("CUDA required")
    if brief.estimated_vram_usage:
        state_data["constraints"].append(f"VRAM: {brief.estimated_vram_usage}")
    return state_data


def is_no_context(path: str | Path) -> bool:
    p = Path(path)
    if not p.exists():
        return True
    try:
        first_line = p.read_text(encoding="utf-8").splitlines()[0]
        return first_line.strip() == NO_CONTEXT_HEADER
    except (OSError, UnicodeDecodeError, IndexError):
        return True


__all__ = [
    "CONTEXT_FILENAME",
    "DeltaBrief",
    "NO_CONTEXT_HEADER",
    "STATE_FILENAME",
    "VALIDATION_REPORT_FILENAME",
    "build_state_payload",
    "is_no_context",
]
