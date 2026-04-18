from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from utils import ask_history
from utils.env_guard import redact_for_display

_SETTINGS_FILE = Path.home() / ".ai-team" / "settings.json"
_LEGACY_SETTINGS_FILE = Path.home() / ".ai-team" / "cli_settings.json"
_DEFAULT_SETTINGS = {
    "theme": "dark",
    "auto_accept_context": False,
    "daily_budget_usd": None,
    "monthly_budget_usd": None,
    "yearly_budget_usd": None,
    "over_budget_continue": False,
    "workflow_view_mode": "chain",
    "help_external_terminal": False,
}

_cli_settings: Optional[dict] = None


def load_cli_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            saved = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**_DEFAULT_SETTINGS, **saved}
            mode = str(merged.get("workflow_view_mode") or "chain").lower()
            merged["workflow_view_mode"] = "list" if mode == "list" else "chain"
            merged["help_external_terminal"] = bool(merged.get("help_external_terminal", False))
            return merged
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return dict(_DEFAULT_SETTINGS)
    if _LEGACY_SETTINGS_FILE.exists():
        try:
            saved = json.loads(_LEGACY_SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**_DEFAULT_SETTINGS, **saved}
            merged["help_external_terminal"] = bool(merged.get("help_external_terminal", False))
            save_cli_settings(merged)
            return merged
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return dict(_DEFAULT_SETTINGS)
    return dict(_DEFAULT_SETTINGS)


def get_cli_settings() -> dict:
    global _cli_settings
    if _cli_settings is None:
        _cli_settings = load_cli_settings()
    return _cli_settings


def save_cli_settings(settings: dict) -> None:
    global _cli_settings
    _SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    merged = {**_DEFAULT_SETTINGS, **settings}
    mode = str(merged.get("workflow_view_mode") or "chain").lower()
    merged["workflow_view_mode"] = "list" if mode == "list" else "chain"
    merged["help_external_terminal"] = bool(merged.get("help_external_terminal", False))
    _SETTINGS_FILE.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    _cli_settings = merged


def _actions_log_path() -> Path:
    p = Path.home() / ".ai-team" / "actions.log"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def log_system_action(action: str, detail: str = "") -> None:
    rec = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "detail": redact_for_display(detail),
    }
    try:
        with open(_actions_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _context_state_path() -> Path:
    p = ask_history.ask_data_dir() / "context_state.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def load_context_state() -> dict:
    p = _context_state_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def save_context_state(state: dict) -> None:
    _context_state_path().write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_context_state(status: str, context_path: Optional[Path] = None, reason: str = "", task_uuid: str = "") -> None:
    state = load_context_state()
    now = datetime.now().isoformat()
    state.update(
        {
            "context_path": str(context_path) if context_path else state.get("context_path", ""),
            "status": status,
            "reason": reason,
            "task_uuid": task_uuid or state.get("task_uuid", ""),
            "updated_at": now,
            "created_at": state.get("created_at", now),
        }
    )
    save_context_state(state)
    log_system_action("context.state.change", f"status={status} reason={reason} path={state.get('context_path','')}")


def is_context_active() -> bool:
    return load_context_state().get("status") == "active"


# ── Model / Prompt overrides ────────────────────────────────────────────────
_OVERRIDES_FILE = Path.home() / ".ai-team" / "model_overrides.json"


def _load_overrides() -> dict:
    if not _OVERRIDES_FILE.exists():
        return {"model_overrides": {}, "prompt_overrides": {}}
    try:
        return json.loads(_OVERRIDES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {"model_overrides": {}, "prompt_overrides": {}}


def _save_overrides(data: dict) -> None:
    _OVERRIDES_FILE.parent.mkdir(parents=True, exist_ok=True)
    _OVERRIDES_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_model_overrides() -> dict:
    return _load_overrides().get("model_overrides", {})


def set_model_override(role_key: str, model_id: str) -> None:
    data = _load_overrides()
    data.setdefault("model_overrides", {})[role_key] = model_id
    _save_overrides(data)
    log_system_action("override.model.set", f"{role_key}={model_id}")


def reset_model_override(role_key: str) -> None:
    data = _load_overrides()
    data.setdefault("model_overrides", {}).pop(role_key, None)
    _save_overrides(data)
    log_system_action("override.model.reset", role_key)


def get_prompt_overrides() -> dict:
    return _load_overrides().get("prompt_overrides", {})


def set_prompt_override(role_key: str, prompt_text: str) -> None:
    data = _load_overrides()
    data.setdefault("prompt_overrides", {})[role_key] = {
        "prompt": prompt_text,
        "updated_at": datetime.now().isoformat(),
    }
    _save_overrides(data)
    log_system_action("override.prompt.set", role_key)


def reset_prompt_override(role_key: str) -> None:
    data = _load_overrides()
    data.setdefault("prompt_overrides", {}).pop(role_key, None)
    _save_overrides(data)
    log_system_action("override.prompt.reset", role_key)


def reset_all_role_overrides(role_key: str) -> None:
    reset_model_override(role_key)
    reset_prompt_override(role_key)


__all__ = [
    "load_cli_settings", "get_cli_settings", "save_cli_settings",
    "log_system_action",
    "load_context_state", "save_context_state", "update_context_state", "is_context_active",
    "get_model_overrides", "set_model_override", "reset_model_override",
    "get_prompt_overrides", "set_prompt_override", "reset_prompt_override",
    "reset_all_role_overrides",
]
