"""
Prompts Package
This package centralizes all system prompts and prompt builders.
Re-exports all prompts for backward compatibility.
"""

from .ambassador import AMBASSADOR_SYSTEM_PROMPT
from .ask_mode import ASK_MODE_SYSTEM_PROMPT
from .btw_coordinator import build_btw_inline_prompt
from .clarification import build_clarification_qa_prompt
from .expert import (
    EXPERT_SYSTEM_PROMPT,
    EXPERT_COPLAN_SYSTEM_PROMPT,
    build_expert_solo_prompt,
    build_expert_coplan_prompt,
)
from .leader import (
    LEADER_SYSTEM_PROMPT,
    _PROJECT_MODE_NOTE,
    build_leader_medium_prompt,
    build_leader_low_prompt,
    build_leader_high_prompt,
)
from .workers import (
    BASE_WORKER_OUTPUT_CONTRACT,
    WORKER_SPECIALIZATIONS,
    build_worker_system_prompt,
    get_worker_prompt,
)

__all__ = [
    "AMBASSADOR_SYSTEM_PROMPT",
    "ASK_MODE_SYSTEM_PROMPT",
    "build_btw_inline_prompt",
    "build_clarification_qa_prompt",
    "EXPERT_SYSTEM_PROMPT",
    "EXPERT_COPLAN_SYSTEM_PROMPT",
    "build_expert_solo_prompt",
    "build_expert_coplan_prompt",
    "LEADER_SYSTEM_PROMPT",
    "_PROJECT_MODE_NOTE",
    "build_leader_medium_prompt",
    "build_leader_low_prompt",
    "build_leader_high_prompt",
    "BASE_WORKER_OUTPUT_CONTRACT",
    "WORKER_SPECIALIZATIONS",
    "build_worker_system_prompt",
    "get_worker_prompt",
]
