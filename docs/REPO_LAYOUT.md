# Repository layout

| Path | Role |
|------|------|
| `agents/` | Agent implementations |
| `core/resources/` | Bundled fonts (PDF/dashboard); see `core.paths` |
| `core/` | CLI, config, dashboard, domain, storage, workflow (`core/cli/python_cli/workflow/runtime/`, `tui/`) |
| `core/domain/skills/` | Skill catalog (`SkillSpec`, registry); add modules under `skills/examples/` or new subpackages |
| `core/api/` | Reserved placeholder for v7.0 REST surface |
| `docs/` | Security, this layout, internal notes |
| `docs/design/` | Placeholder for ADRs / architecture notes |
| `docs/skills_admin/` | Optional skill/admin writeups (was `skillsAdmin/`) |
| `docs/notes/` | Loose notes (e.g. `memory.md`) |
| `scripts/` | Dev runners (`run_aiteam.py`) |
| `tests/` | Pytest |
| `utils/` | Shared utilities |
| `core/bootstrap.py` | `ensure_project_root()` / `REPO_ROOT` |

**Local-only folders (not in git):** delete if present — `.audit-venv/`, `.ruff_cache/`, `.mypy_cache/`, `.graphrag/`.
