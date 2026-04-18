# skillsAdmin (optional)

This folder holds **reference notes and exports for AI assistants** (e.g. Cursor). It is **not** imported by the `aiteam` application at runtime.

- **AgentAudit/** — markdown summaries; generate with `agent-audit` / `python -m agent_audit_standalone` if needed.
- **GraphRag/** — documentation-only snapshots (`PROJECT_MAP.md`, etc.); duplicate Python tooling was removed from here to avoid drift from the real codebase.

To exclude this tree from git locally, add `skillsAdmin/` to `.gitignore`.
