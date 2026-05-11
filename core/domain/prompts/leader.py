_PROJECT_MODE_NOTE = """\
If this is a NEW PROJECT: propose the full directory layout.
If continuing an existing project: skip the full tree; list only files that change.\
"""

LEADER_SYSTEM_PROMPT = """\
You are a Principal Engineer and Technical Planner.
You reason deeply before responding. Your output is an execution-ready context.md, not implementation code.

CLARIFICATION PROTOCOL - CRITICAL:
- If requirements are ambiguous in ways that materially change architecture, scope, data model, or interfaces:
  Output ONLY this JSON object (nothing else - no context.md, no explanation):
  {"type": "clarify", "questions": [{"question": "<Q1>", "options": ["<opt1>", "<opt2>", ...]}, ...]}
- No limit on clarification questions. Provide 3-6 concrete options per question.
- Ask only the high-value clarification questions needed to unblock the plan.
- The old cap "ask at most 2 high-value clarification questions first" is obsolete; ignore it.
- If assumptions are acceptable, proceed directly - output context.md starting with # (no JSON wrapper).
- ABSOLUTE RULE: Your response is EITHER the JSON clarification object OR context.md starting with #. Never both.

Output format (strict, in this exact order):
1) Problem framing
2) Solution architecture
3) Implementation plan
4) Test strategy
5) Risks & rollback
6) Work breakdown
7) Acceptance criteria
8) Self-critique

Required execution sections for the parallel graph:
- Add a "Worker Assignments" subsection with WORKER_A through WORKER_E headings when useful. Each assignment must list exact allowed file paths/globs in backticks.
- Add a "Validation Commands" subsection with terminal checks Secretary should run after all workers finish.

Per implementation step include:
- Goal
- Files (exact paths + function/class names)
- Change (add/update/remove/refactor)
- Risk (low/med/high)
- Validation (concrete check)

Rules:
- No implementation bodies; stubs/signatures/pseudocode only.
- Do not output implementation code, complete code bodies, or sample code blocks.
- Do not output terminal setup commands; Tool Curator decides setup and Secretary executes terminal commands.
- Use precise paths and symbols; avoid vague wording.
- Assign each atomic task to the best-suited worker by name.
- Secretary owns all terminal commands; workers write files only and may suggest commands, but do not execute them.
- HARD tasks must include HARDWARE line per step (CPU/GPU and VRAM estimate when relevant).
- No code fences around the final document.
"""

_CLARIFICATION_REMINDER = """\
Remember the clarification protocol from your system prompt:
- If ambiguous: output ONLY the JSON clarification object and ask as many high-value questions as needed.
- Do not merely ask up to 2 high-value clarification questions when more are needed.
- If clear: output context.md starting with # (no JSON wrapper).
"""


def _build_worker_roster() -> str:
    """Build a compact worker roster without importing config at module import time."""
    try:
        from core.config import config

        rows = []
        for worker in config.list_workers():
            if str(worker.get("tier", "")).upper() != "WORKER":
                continue
            wid = str(worker.get("id") or "").upper()
            role = str(worker.get("role") or "Worker")
            model = str(worker.get("model") or "")
            reason = str(worker.get("reason") or "").strip()
            tail = f" - {reason}" if reason else ""
            rows.append(f"- {wid}: {role} ({model}){tail}")
        return "\n".join(rows) if rows else "- WORKER_A: General implementation worker"
    except Exception:
        return "- WORKER_A: General implementation worker"


def _build_leader_prompt(
    state_str: str,
    *,
    tier: str,
    mission: str,
    tier_rule: str,
    steps_rule: str,
    tier_notes: list[str],
) -> str:
    notes = "\n".join(f"- {note}" for note in tier_notes)
    return (
        "## Mission\n"
        f"{mission}\n\n"
        f"## Project state\n{state_str}\n\n"
        f"{_PROJECT_MODE_NOTE}\n\n"
        f"{_CLARIFICATION_REMINDER}\n"
        "## Worker Roster (your sub-agents)\n"
        "You have the following workers available. Assign tasks to the most suitable worker:\n"
        f"{_build_worker_roster()}\n\n"
        "## Naming Convention Protocol\n"
        "Before generating context.md, establish and document in Section 2:\n"
        "1. Function naming style\n"
        "2. Variable naming conventions\n"
        "3. Type/interface naming conventions\n"
        "4. Module/package structure conventions\n"
        "5. Error handling patterns\n"
        "All workers must follow these conventions to avoid conflicts.\n\n"
        "## Constraints\n"
        f"- Tier: {tier} - {tier_rule}\n"
        "- Hard requirements: every file that changes must be named; every function stub must have a signature; "
        "every step must name concrete files and symbols\n"
        "- Every atomic task must name the assigned worker id and why that worker fits\n"
        "- Non-goals: do not design beyond the stated task scope\n"
        "- NFRs: note any performance, security, or concurrency constraints explicitly\n"
        f"- Steps: {steps_rule} ordered by dependency\n"
        f"{notes}\n\n"
        "Write context.md now following the 8-section format in your system prompt.\n"
        "Work breakdown (section 6): every task independently testable.\n"
        "Acceptance criteria (section 7): concrete pass/fail checks.\n"
        "Self-critique (section 8): name weak assumptions and any spike needed."
    )


def build_leader_medium_prompt(state_str: str) -> str:
    return _build_leader_prompt(
        state_str,
        tier="MEDIUM",
        mission="Design the best possible implementation plan for the task below.",
        tier_rule="multi-file feature, ~1 day of focused work",
        steps_rule="5-8 items",
        tier_notes=[
            "Non-goals: do not design beyond the stated task scope",
            "Work breakdown (section 6): every task independently testable",
        ],
    )


def build_leader_low_prompt(state_str: str) -> str:
    return _build_leader_prompt(
        state_str,
        tier="LOW",
        mission="Design a focused, actionable plan for the task below.",
        tier_rule="single component, module, or quick feature; <1 hour to implement",
        steps_rule="3-6 items",
        tier_notes=[
            "Scope: Q&A-to-plan, code skeleton, function plan, simple feature outline, bug fix, or single-class guide",
            "Sections 4, 5, and 6: 1-3 bullets each",
            "Section 7: at least 2 pass/fail checks",
        ],
    )


def build_leader_high_prompt(state_str: str) -> str:
    return _build_leader_prompt(
        state_str,
        tier="HARD",
        mission="Design a comprehensive, production-grade implementation plan for the task below.",
        tier_rule="GPU/CUDA, distributed systems, or platform-level architecture",
        steps_rule="8-12 items",
        tier_notes=[
            "HARDWARE line required on every step (CPU / GPU, VRAM estimate)",
            "NFRs: document CPU/GPU boundaries, VRAM budgets, concurrency hazards, and security boundaries explicitly",
            "Section 5: cover data loss, migration, and security for every high-risk step",
            "Self-critique: identify at least one spike needed before full implementation",
        ],
    )
