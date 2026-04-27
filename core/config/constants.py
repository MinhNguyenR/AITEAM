"""Shared numeric limits for agents and API behavior."""
from pathlib import Path

# Leader: JSON state embedded in prompt
STATE_CHAR_LIMIT_DEFAULT = 3000
STATE_CHAR_LIMIT_LOW = 1500

# BaseAgent retry / backoff (mirrors BaseAgent class attrs for single import site)
API_MAX_RETRIES = 6
API_BASE_BACKOFF_SEC = 2.0

# HTTP client timeouts (used by OpenAI/httpx clients and urllib downloads)
HTTP_CONNECT_TIMEOUT_SEC = 10.0
HTTP_READ_TIMEOUT_SEC = 120.0
HTTP_DOWNLOAD_MAX_BYTES = 5 * 1024 * 1024
HTTP_JSON_MAX_BYTES = 5 * 1024 * 1024
PROJECT_FILE_MAX_BYTES = 2 * 1024 * 1024
VAULT_DECOMPRESS_MAX_BYTES = 16 * 1024 * 1024

# Hardware
VRAM_USAGE_FACTOR = 0.8

# Local data paths
AI_TEAM_HOME = Path.home() / ".ai-team"
SETTINGS_FILE = AI_TEAM_HOME / "settings.json"
LEGACY_SETTINGS_FILE = AI_TEAM_HOME / "cli_settings.json"
ACTIONS_LOG_FILE = AI_TEAM_HOME / "actions.log"
MODEL_OVERRIDES_FILE = AI_TEAM_HOME / "model_overrides.json"

# Env var names
ENV_OPENROUTER_API_KEY = "OPENROUTER_API_KEY"
ENV_OPENROUTER_BASE_URL = "OPENROUTER_BASE_URL"
ENV_VAULT_KEY = "AI_TEAM_VAULT_KEY"
ENV_ALLOW_UNENCRYPTED_VAULT = "AI_TEAM_ALLOW_UNENCRYPTED_VAULT"
ENV_MAX_VRAM_LIMIT = "MAX_VRAM_LIMIT"
