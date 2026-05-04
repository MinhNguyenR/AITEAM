from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Optional

from core.config.constants import LEGACY_SETTINGS_FILE, SETTINGS_FILE

from ._io import write_secure

_DEFAULT_SETTINGS = {
    "theme": "dark",
    "workflow_view_mode": "chain",
    "auto_accept_context": False,
    "auto_context_action": "ask",
    "daily_budget_usd": None,
    "monthly_budget_usd": None,
    "yearly_budget_usd": None,
    "over_budget_continue": False,
    "help_external_terminal": False,
    "display_language": "vi",
}

_cli_settings: Optional[dict] = None
_cli_settings_lock = threading.Lock()


def _settings_file() -> Path:
    return Path.home() / ".ai-team" / SETTINGS_FILE.name


def _legacy_settings_file() -> Path:
    return Path.home() / ".ai-team" / LEGACY_SETTINGS_FILE.name


def _normalize_settings(settings: dict) -> dict:
    merged = {**_DEFAULT_SETTINGS, **settings}
    mode = str(merged.get("workflow_view_mode") or "chain").strip().lower()
    merged["workflow_view_mode"] = "list" if mode == "list" else "chain"
    merged["help_external_terminal"] = bool(merged.get("help_external_terminal", False))
    action = str(merged.get("auto_context_action") or "ask").lower()
    merged["auto_context_action"] = action if action in ("ask", "accept", "decline") else "ask"
    return merged


def load_cli_settings() -> dict:
    settings_file = _settings_file()
    legacy_file = _legacy_settings_file()
    if settings_file.exists():
        try:
            saved = json.loads(settings_file.read_text(encoding="utf-8"))
            return _normalize_settings(saved)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return dict(_DEFAULT_SETTINGS)
    if legacy_file.exists():
        try:
            saved = json.loads(legacy_file.read_text(encoding="utf-8"))
            merged = _normalize_settings(saved)
            save_cli_settings(merged)
            return merged
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return dict(_DEFAULT_SETTINGS)
    return dict(_DEFAULT_SETTINGS)


def get_cli_settings() -> dict:
    global _cli_settings
    with _cli_settings_lock:
        if _cli_settings is None:
            _cli_settings = load_cli_settings()
        return dict(_cli_settings)


def save_cli_settings(settings: dict) -> None:
    global _cli_settings
    merged = _normalize_settings(settings)
    write_secure(_settings_file(), json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    with _cli_settings_lock:
        _cli_settings = merged


__all__ = ["get_cli_settings", "load_cli_settings", "save_cli_settings"]
