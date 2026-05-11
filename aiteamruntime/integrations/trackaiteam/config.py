from __future__ import annotations

DEFAULT_AGENT_LANES = (
    "Ambassador",
    "Leader",
    "Tool Curator",
    "Secretary",
    "Worker A",
    "Worker B",
    "Worker C",
    "Worker D",
    "Worker E",
    "Explainer",
)

WORKER_REGISTRY = {
    "Worker A": {"role": "implementation", "reason": "general code changes and narrow feature work"},
    "Worker B": {"role": "tests", "reason": "focused tests, regression checks, and fixtures"},
    "Worker C": {"role": "frontend", "reason": "viewer, assets, and user workflow polish"},
    "Worker D": {"role": "runtime", "reason": "orchestration, scheduling, and resource coordination"},
    "Worker E": {"role": "docs", "reason": "summaries, handoff notes, and final packaging"},
}
