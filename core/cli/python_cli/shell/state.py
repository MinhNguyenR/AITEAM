from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from core.config.constants import (
    ACTIONS_LOG_FILE,
    AI_TEAM_HOME,
    LEGACY_SETTINGS_FILE,
    MODEL_OVERRIDES_FILE,
    SETTINGS_FILE,
)
from core.storage import ask_history
from utils.env_guard import redact_for_display

logger = logging.getLogger(__name__)
_crypto_warned = False


def _write_secure(path: Path, data: str) -> None:
    """Write text to file then chmod 0o600 (POSIX); no-op chmod on Windows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding="utf-8")
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass


_SETTINGS_FILE = SETTINGS_FILE
_LEGACY_SETTINGS_FILE = LEGACY_SETTINGS_FILE
_DEFAULT_SETTINGS = {
    "theme": "dark",
    "auto_accept_context": False,
    "auto_context_action": "ask",  # ask | accept | decline — on context gate / delete
    "daily_budget_usd": None,
    "monthly_budget_usd": None,
    "yearly_budget_usd": None,
    "over_budget_continue": False,
    "help_external_terminal": False,
    "display_language": "vi",  # vi | en
}

_cli_settings: Optional[dict] = None
_cli_settings_lock = threading.Lock()


def load_cli_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            saved = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = {**_DEFAULT_SETTINGS, **saved}
            merged.pop("workflow_view_mode", None)
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
    with _cli_settings_lock:
        if _cli_settings is None:
            _cli_settings = load_cli_settings()
        return dict(_cli_settings)


def save_cli_settings(settings: dict) -> None:
    global _cli_settings
    merged = {**_DEFAULT_SETTINGS, **settings}
    merged.pop("workflow_view_mode", None)
    merged["help_external_terminal"] = bool(merged.get("help_external_terminal", False))
    aca = str(merged.get("auto_context_action") or "ask").lower()
    merged["auto_context_action"] = aca if aca in ("ask", "accept", "decline") else "ask"
    _write_secure(_SETTINGS_FILE, json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    with _cli_settings_lock:
        _cli_settings = merged


def _actions_log_path() -> Path:
    ACTIONS_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    return ACTIONS_LOG_FILE


def log_system_action(action: str, detail: str = "") -> None:
    rec = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "detail": redact_for_display(detail),
    }
    p = _actions_log_path()
    try:
        is_new = not p.exists()
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if is_new and os.name != "nt":
            try:
                os.chmod(p, 0o600)
            except OSError:
                pass
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
    _write_secure(_context_state_path(), json.dumps(state, indent=2, ensure_ascii=False) + "\n")


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
_OVERRIDES_FILE = MODEL_OVERRIDES_FILE


def _load_overrides() -> dict:
    if not _OVERRIDES_FILE.exists():
        return {"model_overrides": {}, "prompt_overrides": {}, "sampling_overrides": {}}
    try:
        data = json.loads(_OVERRIDES_FILE.read_text(encoding="utf-8"))
        data.setdefault("sampling_overrides", {})
        return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {"model_overrides": {}, "prompt_overrides": {}, "sampling_overrides": {}}


def _save_overrides(data: dict) -> None:
    _write_secure(_OVERRIDES_FILE, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


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


def _warn_crypto_fallback_once(action: str) -> None:
    global _crypto_warned
    if _crypto_warned:
        return
    _crypto_warned = True
    logger.warning(
        "[state] prompt %s unavailable — vault key missing or cryptography failed; "
        "storing/reading plaintext fallback", action,
    )


def _encrypt_prompt(text: str) -> dict:
    """Encrypt prompt text with vault Fernet if available, else store plaintext."""
    try:
        from core.config import Config
        from core.storage.knowledge.vault_key import load_or_create_vault_key
        from cryptography.fernet import Fernet

        key = load_or_create_vault_key(Config.BASE_DIR)
        if key:
            token = Fernet(key.encode("ascii")).encrypt(text.encode("utf-8")).decode("ascii")
            return {"enc": token, "encrypted": True}
    except Exception:
        logger.debug("[state] prompt encrypt failed", exc_info=True)
    _warn_crypto_fallback_once("encryption")
    return {"prompt": text, "encrypted": False}


def _decrypt_prompt(entry: dict) -> str:
    if not entry.get("encrypted"):
        return entry.get("prompt", "")
    try:
        from core.config import Config
        from core.storage.knowledge.vault_key import load_or_create_vault_key
        from cryptography.fernet import Fernet

        key = load_or_create_vault_key(Config.BASE_DIR)
        if key:
            return Fernet(key.encode("ascii")).decrypt(entry["enc"].encode("ascii")).decode("utf-8")
    except Exception:
        logger.debug("[state] prompt decrypt failed", exc_info=True)
    _warn_crypto_fallback_once("decryption")
    return ""


def get_prompt_overrides() -> dict:
    raw = _load_overrides().get("prompt_overrides", {})
    return {k: {**v, "prompt": _decrypt_prompt(v)} for k, v in raw.items()}


def set_prompt_override(role_key: str, prompt_text: str) -> None:
    data = _load_overrides()
    entry = _encrypt_prompt(prompt_text)
    entry["updated_at"] = datetime.now().isoformat()
    data.setdefault("prompt_overrides", {})[role_key] = entry
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


def get_sampling_overrides() -> dict[str, Any]:
    return _load_overrides().get("sampling_overrides", {}) or {}


def update_sampling_override(role_key: str, **kwargs: Any) -> None:
    data = _load_overrides()
    rk = str(role_key or "").upper()
    bucket: dict[str, Any] = dict(data.setdefault("sampling_overrides", {}).get(rk) or {})
    for k in ("temperature", "top_p", "max_tokens", "reasoning_effort"):
        if k in kwargs and kwargs[k] is not None:
            bucket[k] = kwargs[k]
    data.setdefault("sampling_overrides", {})[rk] = bucket
    _save_overrides(data)
    log_system_action("override.sampling.set", f"{rk}={bucket}")


def reset_sampling_override(role_key: str | None = None) -> None:
    data = _load_overrides()
    if role_key:
        data.setdefault("sampling_overrides", {}).pop(str(role_key).upper(), None)
    else:
        data["sampling_overrides"] = {}
    _save_overrides(data)
    log_system_action("override.sampling.reset", str(role_key or "ALL"))


__all__ = [
    "load_cli_settings", "get_cli_settings", "save_cli_settings",
    "log_system_action",
    "load_context_state", "save_context_state", "update_context_state", "is_context_active",
    "get_model_overrides", "set_model_override", "reset_model_override",
    "get_prompt_overrides", "set_prompt_override", "reset_prompt_override",
    "reset_all_role_overrides",
    "get_sampling_overrides", "update_sampling_override", "reset_sampling_override",
]
