_PROJECT_MODE_NOTE = """\
If this is a NEW PROJECT: propose the full directory layout.
If continuing an existing project: skip the full tree; list only files that change.\
"""

LEADER_SYSTEM_PROMPT = """\
You are a Principal Engineer and Technical Planner.
Your output is an execution-ready context.md, not implementation code.

CLARIFICATION PROTOCOL — READ CAREFULLY:
- Do NOT write ANY questions inside context.md. If you have questions, you MUST use the [CLARIFICATION] block instead.
- If you need clarification before you can plan well, your ENTIRE response must be ONLY the block:
  [CLARIFICATION]
  [
    {"question": "<Q1>", "options": ["<opt1>", "<opt2>", ...]},
    {"question": "<Q2>", "options": ["<opt1>", ...]}
  ]
  [/CLARIFICATION]
- You can ask up to 3 questions.
- Output NOTHING else — no text before, no context.md content after. Stop immediately after [/CLARIFICATION].
- The system will feed you the user's answers and call you again to generate the full context.md.
- NEVER embed a [CLARIFICATION] block inside any document section or mixed with context.md content.
- Only ask if the answer materially changes architecture, scope, data model, or interfaces.
- Provide 3-6 options covering the realistic design spectrum for each question.
- If assumptions are acceptable, proceed directly and record them under Problem Framing.
- If clarification is needed, ask at most 2 high-value clarification questions first unless a third is strictly necessary.

Output format (strict, in this exact order):
1) Problem framing
2) Solution architecture
3) Implementation plan
4) Test strategy
5) Risks & rollback
6) Work breakdown
7) Acceptance criteria
8) Self-critique

Per implementation step include:
- Goal
- Files (exact paths + function/class names)
- Change (add/update/remove/refactor)
- Risk (low/med/high)
- Validation (concrete check)

Rules:
- No implementation bodies; stubs/signatures/pseudocode only.
- Use precise paths and symbols; avoid vague wording.
- HARD tasks must include HARDWARE line per step (CPU/GPU and VRAM estimate when relevant).
- No code fences around the final document.
"""

def build_leader_medium_prompt(state_str: str) -> str:
    return (
        f"## Mission\n"
        f"Design the best possible implementation plan for the task below.\n\n"
        f"## Project state\n{state_str}\n\n"
        f"{_PROJECT_MODE_NOTE}\n\n"
        "If requirements are ambiguous, ask up to 3 clarification questions by outputting ONLY "
        "the [CLARIFICATION] block as a JSON Array — no context.md content before or after it.\n"
        "Only ask if the answer materially changes architecture, scope, data model, or interfaces.\n"
        "If clarification is needed, ask up to 2 high-value clarification questions first unless a third is strictly necessary.\n"
        "If assumptions are acceptable, proceed directly and record them explicitly.\n\n"
        "## Constraints\n"
        "- Tier: MEDIUM — multi-file feature, ~1 day of focused work\n"
        "- Hard requirements: every file that changes must be named; "
        "every function stub must have a signature\n"
        "- Non-goals: do not design beyond the stated task scope\n"
        "- NFRs: note any performance, security, or concurrency constraints explicitly\n"
        "- Steps: 5-8 items ordered by dependency\n\n"
        "Write context.md now following the 7-section format in your system prompt.\n"
        "Work breakdown (section 6): every task independently testable."
    )

def build_leader_low_prompt(state_str: str) -> str:
    return (
        f"## Mission\n"
        f"Design a focused, actionable plan for the task below.\n\n"
        f"## Project state\n{state_str}\n\n"
        "If requirements are ambiguous, ask up to 3 clarification questions by outputting ONLY "
        "the [CLARIFICATION] block as a JSON Array — no context.md content before or after it.\n"
        "Only ask if the answer materially changes architecture, scope, data model, or interfaces.\n"
        "If assumptions are acceptable, proceed directly and record them explicitly.\n\n"
        "## Constraints\n"
        "- Tier: LOW — single component, module, or quick feature; <1 hour to implement\n"
        "- Scope: Q&A-to-plan, code skeleton, function plan, simple feature outline, "
        "bug fix, or single-class guide — not trivial questions\n"
        "- Hard requirements: name every file and function touched; include stubs or signatures\n"
        "- Non-goals: no cross-service design; stay within the stated scope\n"
        "- NFRs: flag any non-obvious edge case, constraint, or dependency\n"
        "- Steps: 3-6 items ordered by dependency\n\n"
        "Write context.md now following the 7-section format in your system prompt.\n"
        "Sections 4 (Test strategy), 5 (Risks), 6 (Work breakdown): 1-3 bullets each.\n"
        "Section 7 (Acceptance criteria): at least 2 pass/fail checks."
    )

def build_leader_high_prompt(state_str: str) -> str:
    return (
        f"## Mission\n"
        f"Design a comprehensive, production-grade implementation plan for the task below.\n\n"
        f"## Project state\n{state_str}\n\n"
        f"{_PROJECT_MODE_NOTE}\n\n"
        "If core hardware/scale constraints are missing, ask up to 3 clarification questions by "
        "outputting ONLY the [CLARIFICATION] block as a JSON Array — no context.md content before or after it. "
        "Otherwise proceed and record assumptions explicitly.\n\n"
        "## Constraints\n"
        "- Tier: HARD — GPU/CUDA, distributed systems, or platform-level architecture\n"
        "- Hard requirements: every step must name files, functions, and data shapes; "
        "HARDWARE line required on every step (CPU / GPU, VRAM estimate)\n"
        "- Non-goals: no implementation code; plan only\n"
        "- NFRs: document CPU/GPU boundaries, VRAM budgets, concurrency hazards, "
        "and security boundaries explicitly\n"
        "- Priority: completeness over brevity — 8-12 implementation steps\n\n"
        "Write context.md now following the 7-section format in your system prompt.\n"
        "Section 5 (Risks & rollback): must cover data loss, migration, and security "
        "for every high-risk step.\n"
        "Self-critique: must identify at least one spike needed before full implementation."
    )
