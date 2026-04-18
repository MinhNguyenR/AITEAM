"""Shared numeric limits for agents and API behavior."""

# Leader: JSON state embedded in prompt
STATE_CHAR_LIMIT_DEFAULT = 3000
STATE_CHAR_LIMIT_LOW = 1500

# BaseAgent retry / backoff (mirrors BaseAgent class attrs for single import site)
API_MAX_RETRIES = 6
API_BASE_BACKOFF_SEC = 2.0
