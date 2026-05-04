"""Constants shared across all monitor sub-modules."""
from __future__ import annotations
from core.cli.python_cli.i18n import t

_GEN_STEPS = frozenset({"ambassador", "leader_generate", "tool_curator"})
_SPINNER   = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"

# Note: These are base keys or fallback labels. 
# We use t() in _utils.py or elsewhere to get the actual localized text.

_ROLE: dict[str, str] = {
    "ambassador":         t("pipeline.ambassador"),
    "leader_generate":    t("pipeline.leader"),
    "human_context_gate": t("gate.human_gate"),
    "tool_curator":       t("pipeline.tool_curator"),
    "finalize_phase1":    t("pipeline.finalize"),
}

_ACTION: dict[str, str] = {
    "ambassador":         t("pipeline.gen_state_doing"),
    "leader_generate":    t("pipeline.gen_context_doing"),
    "human_context_gate": t("pipeline.review_context_doing"),
    "tool_curator":       t("pipeline.gen_tools_doing"),
    "finalize_phase1":    t("pipeline.finalize_doing"),
}

_ACTION_DONE: dict[str, str] = {
    "ambassador":         t("pipeline.gen_state_doing"),
    "leader_generate":    t("pipeline.gen_context"),
    "human_context_gate": t("pipeline.review_context_doing"),
    "tool_curator":       t("pipeline.gen_tools"),
    "finalize_phase1":    t("pipeline.finalize_doing"),
}

def get_action_label(step_id: str, done: bool = False) -> str:
    if done:
        return {
            "ambassador":         t("pipeline.gen_state_doing"),
            "leader_generate":    t("pipeline.gen_context"),
            "human_context_gate": t("pipeline.review_context_doing"),
            "tool_curator":       t("pipeline.gen_tools"),
            "finalize_phase1":    t("pipeline.finalize_doing"),
        }.get(step_id, step_id)
    return {
        "ambassador":         t("pipeline.gen_state_doing"),
        "leader_generate":    t("pipeline.gen_context_doing"),
        "human_context_gate": t("pipeline.review_context_doing"),
        "tool_curator":       t("pipeline.gen_tools_doing"),
        "finalize_phase1":    t("pipeline.finalize_doing"),
    }.get(step_id, step_id)
import re
_CLEAR_TEXT_RE = re.compile(
    r'\s*/clear\s+text(?:\s+(\S+?)(?:\s+(\d+))?)?\s*$',
    re.IGNORECASE,
)

_CMD_HINT = t("cmd.palette_hint")

_GATE_WAITING  = "waiting"
_GATE_ACCEPTED = "accepted"
_GATE_DECLINED = "declined"
_GATE_REGEN    = "regen"
