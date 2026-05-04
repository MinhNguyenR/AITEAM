# Changelog

All notable changes to **AI Team Blueprint** are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [6.2.1] — 2026-04-27

### Security
- HTTP timeouts on all OpenAI/`httpx` clients (connect 10s / read 120s) via shared `make_openai_client`.
- 5MB cap on font downloads (`exporters.py`), OpenRouter pricing/free-model JSON payloads, and project file reads.
- `subprocess.Popen` editor invocation in `list_view.py` switched to `safe_editor.build_editor_argv`.
- POSIX `chmod 0o600` on user state files (`settings.json`, `actions.log`, `context_state.json`, `model_overrides.json`).
- `agents/_api_client.py` debug logs now route raw exception text through `redact_for_display`.
- `zlib` decompression bomb cap (`VAULT_DECOMPRESS_MAX_BYTES = 16MB`) in `sqlite_repository`.
- Extended `redact_for_display` patterns: `password=`, `secret=`, `token=`, `api_key=`, generic 40+ char tokens.
- TOCTOU fix in `base_agent.log_action` (open `"a"` directly instead of `exists()` + `open`).
- `read_project_file` now rejects files larger than `PROJECT_FILE_MAX_BYTES = 2MB`.

### Changed
- `core/cli/pythonCli/` → `core/cli/python_cli/` rename across codebase, tests, docs, packaging.
- `core/config/registry.py` split into `core/config/registry/coding/*.py` (one file per role).
- Centralized constants in `core/config/constants.py`: `AI_TEAM_HOME`, HTTP/size caps, `VRAM_USAGE_FACTOR`, env var names.
- `agents/_api_client.py` `call_api` / `call_api_stream` refactored into `_preflight_budget`, `_record_completion_usage`, `_handle_retry_error`.
- Crypto fallback in `state.py` now logs warning once instead of silent plaintext store.
- BTW inline streaming extracted into `_btw_inline.py` shared by `list_view` and `monitor_app`.

### Fixed
- `start_flow.run_agent_graph` broad `except Exception: pass` replaced with logged error + pipeline status.
- `monitor_app` role lookup logs at debug level instead of swallowing silently.
- Type hints added to `chat_completions_create*`, `ChatAgent.ask`, `ConfigService.list_workers`.

### Removed
- Empty `core/orchestrator.py`.
- Unused `langchain-core` and `langsmith` dependencies.

### Added
- `tests/test_free_model_finder.py`, `tests/test_chat_agent.py`.

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
