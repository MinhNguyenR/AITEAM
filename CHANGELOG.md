# Changelog

All notable changes to **AI Team Blueprint** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [6.2.0] — 2026-04-22

### Security
- First-run interactive prompt for `OPENROUTER_API_KEY` — key never needs to be pre-placed in `.env`.
- Allowlist validation on `OPENROUTER_BASE_URL` (only `openrouter.ai` / `api.openrouter.ai` accepted).
- Vault fail-closed: `_vault_wrap` now raises `VaultMissingKeyError` instead of silently storing plaintext.
- `AI_TEAM_VAULT_KEY` no longer written to `os.environ`; cached in module memory only.
- Symlink-escape guard in `read_project_file` via `Path.resolve()` + `is_relative_to`.
- Narrowed `except Exception: pass` blocks in Ambassador and `_api_client`.
- Added Gitleaks secret scanning to CI + `.pre-commit-config.yaml`.

### Fixed
- `pyproject.toml` version bumped from `"0"` to `"6.2.0"`.
- FTS5 double-quote escape in `graphrag_store.search_fts`.
- Workflow `activity_log` now applies `redact_for_display` before writing.
- API error logs now only emit exception type + status code (no upstream body).

### Changed
- `.env` is no longer required at startup; the CLI prompts if missing.
- `core/domain/agent_protocol.py` — `AgentProtocol` interface reduces `core ↔ agents` coupling.
- `run_start` refactored into four focused helpers (`_classify_task`, `_generate_context`, `_approval_gate`, `_persist_run`).
- Mypy scope expanded to `core agents utils` in CI.
- Coverage omit list trimmed; `.coverage` / `aiteam.egg-info/` added to `.gitignore`.

### Removed
- `package.json`, `package-lock.json` (no Node.js code in project).
- Empty `utils/free_model_finder.py` replaced with real free-model finder feature.

---

## [6.1.x] and earlier

See git log for full history.
