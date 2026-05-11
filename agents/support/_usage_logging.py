"""Usage logging helpers shared by API client code."""
from __future__ import annotations


ROLE_TO_WORKFLOW_NODE = {
    "AMBASSADOR": "ambassador",
    "LEADER_MEDIUM": "leader_generate",
    "LEADER_LOW": "leader_generate",
    "LEADER_HIGH": "leader_generate",
    "TOOL_CURATOR": "tool_curator",
    "SECRETARY": "secretary",
}


def log_workflow_usage(role_key: str, target_model: str, prompt_tokens: int, completion_tokens: int) -> None:
    try:
        from utils.logger import workflow_event

        node = ROLE_TO_WORKFLOW_NODE.get(str(role_key or "").upper())
        if node:
            workflow_event(
                node,
                "usage",
                f"model={target_model} prompt_tokens={prompt_tokens} completion_tokens={completion_tokens}",
            )
    except Exception:
        pass
