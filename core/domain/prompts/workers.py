from __future__ import annotations

from typing import Any


BASE_WORKER_OUTPUT_CONTRACT = """\
Output format (STRICT - use exactly these delimiters):

--- FILE: path/to/file.py ---
<complete new file content>
--- END FILE ---

--- COMMANDS ---
<validation commands only; never setup/scaffold commands>
--- END COMMANDS ---

Rules:
- Output COMPLETE file content, not diffs.
- Only modify files assigned to you through allowed paths.
- Do not run terminal commands. Secretary is the only role that executes commands.
- Do not create projects or install dependencies with terminal commands.
- You may suggest up to 5 validation commands, but not setup/scaffold commands.
- If setup/scaffold is missing, ask Leader/Secretary instead of inventing commands.
"""


WORKER_SPECIALIZATIONS: dict[str, dict[str, str]] = {
    "WORKER_A": {
        "title": "Backend / implementation specialist",
        "focus": "general code changes, backend logic, data flow, and narrow feature implementation",
    },
    "WORKER_B": {
        "title": "Fullstack / tests specialist",
        "focus": "focused tests, fixtures, regression checks, API integration, and behavior verification",
    },
    "WORKER_C": {
        "title": "Frontend / UI specialist",
        "focus": "viewer code, React/UI assets, user workflows, accessibility, and visual polish",
    },
    "WORKER_D": {
        "title": "Runtime / systems specialist",
        "focus": "orchestration, scheduling, resource coordination, state machines, and concurrency boundaries",
    },
    "WORKER_E": {
        "title": "Docs / packaging specialist",
        "focus": "handoff notes, summaries, integration docs, release notes, and final packaging details",
    },
}


def get_worker_prompt(worker_key: str, registry_config: dict[str, Any] | None = None) -> str:
    key = str(worker_key or "WORKER_A").upper()
    spec = WORKER_SPECIALIZATIONS.get(key, WORKER_SPECIALIZATIONS["WORKER_A"])
    role = str((registry_config or {}).get("role") or spec["title"])
    reason = str((registry_config or {}).get("reason") or spec["focus"])
    return (
        f"You are {key}: {role}.\n"
        f"Specialization: {reason}\n\n"
        "Operate as a focused implementation sub-agent. Stay inside your assignment, "
        "honor project conventions, and coordinate through the trace rather than by "
        "running commands yourself.\n\n"
        f"{BASE_WORKER_OUTPUT_CONTRACT}"
    )


def build_worker_system_prompt(worker_key: str, registry_config: dict[str, Any] | None = None) -> str:
    return get_worker_prompt(worker_key, registry_config)


__all__ = ["BASE_WORKER_OUTPUT_CONTRACT", "WORKER_SPECIALIZATIONS", "get_worker_prompt", "build_worker_system_prompt"]
