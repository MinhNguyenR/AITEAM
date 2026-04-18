# Developer tools (optional)

These live at the repository root as Python packages so `pip install -e .` can expose console scripts:

- **`agent_audit_standalone/`** — `agent-audit` / `python -m agent_audit_standalone` for agent coverage reports.

The main application (`aiteam`) does not import these modules. Use them from the shell when auditing the codebase.
