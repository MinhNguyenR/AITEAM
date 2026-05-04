from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Optional

from core.app_state import actions as _actions
from core.app_state import context_state as _context
from core.app_state import overrides as _overrides
from core.app_state import settings as _settings
from core.config.constants import (
    ACTIONS_LOG_FILE,
    LEGACY_SETTINGS_FILE,
    MODEL_OVERRIDES_FILE,
    SETTINGS_FILE,
)

logger = logging.getLogger(__name__)


_SETTINGS_FILE = SETTINGS_FILE
_LEGACY_SETTINGS_FILE = LEGACY_SETTINGS_FILE
_DEFAULT_SETTINGS = dict(_settings._DEFAULT_SETTINGS)
_cli_settings: Optional[dict] = None
_cli_settings_lock = threading.Lock()

_context_state_path = _context._context_state_path

_OVERRIDES_FILE = MODEL_OVERRIDES_FILE
_crypto_warned = False


def _write_secure(path: Path, data: str) -> None:
    _settings.write_secure(path, data)


def load_cli_settings() -> dict:
    if _SETTINGS_FILE.exists():
        try:
            saved = json.loads(_SETTINGS_FILE.read_text(encoding="utf-8"))
            return _settings._normalize_settings(saved)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return dict(_DEFAULT_SETTINGS)
    if _LEGACY_SETTINGS_FILE.exists():
        try:
            saved = json.loads(_LEGACY_SETTINGS_FILE.read_text(encoding="utf-8"))
            merged = _settings._normalize_settings(saved)
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
    merged = _settings._normalize_settings(settings)
    _write_secure(_SETTINGS_FILE, json.dumps(merged, indent=2, ensure_ascii=False) + "\n")
    with _cli_settings_lock:
        _cli_settings = merged


def _actions_log_path() -> Path:
    path = Path.home() / ".ai-team" / ACTIONS_LOG_FILE.name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_system_action(action: str, detail: str = "") -> None:
    rec = {
        "timestamp": _actions.datetime.now().isoformat(),
        "action": action,
        "detail": _actions.redact_for_display(detail),
    }
    path = _actions_log_path()
    try:
        is_new = not path.exists()
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if is_new and _actions.os.name != "nt":
            try:
                _actions.os.chmod(path, 0o600)
            except OSError:
                pass
    except OSError:
        pass


def load_context_state() -> dict:
    path = _context_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def save_context_state(state: dict) -> None:
    _write_secure(_context_state_path(), json.dumps(state, indent=2, ensure_ascii=False) + "\n")


def update_context_state(
    status: str,
    context_path: Optional[Path] = None,
    reason: str = "",
    task_uuid: str = "",
) -> None:
    state = load_context_state()
    now = _context.datetime.now().isoformat()
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
    log_system_action(
        "context.state.change",
        f"status={status} reason={reason} path={state.get('context_path', '')}",
    )


def is_context_active() -> bool:
    return load_context_state().get("status") == "active"


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
        "[state] prompt %s unavailable - vault key missing or cryptography failed; storing/reading plaintext fallback",
        action,
    )


def _encrypt_prompt(text: str) -> dict:
    try:
        return _overrides._encrypt_prompt(text)
    except Exception:
        logger.debug("[state] prompt encrypt failed", exc_info=True)
        _warn_crypto_fallback_once("encryption")
        return {"prompt": text, "encrypted": False}


def _decrypt_prompt(entry: dict) -> str:
    try:
        text = _overrides._decrypt_prompt(entry)
    except Exception:
        logger.debug("[state] prompt decrypt failed", exc_info=True)
        _warn_crypto_fallback_once("decryption")
        return ""
    if entry.get("encrypted") and not text:
        _warn_crypto_fallback_once("decryption")
    return text


def get_prompt_overrides() -> dict:
    raw = _load_overrides().get("prompt_overrides", {})
    return {key: {**value, "prompt": _decrypt_prompt(value)} for key, value in raw.items()}


def set_prompt_override(role_key: str, prompt_text: str) -> None:
    data = _load_overrides()
    entry = _encrypt_prompt(prompt_text)
    entry["updated_at"] = _overrides.datetime.now().isoformat()
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
    role = str(role_key or "").upper()
    bucket: dict[str, Any] = dict(data.setdefault("sampling_overrides", {}).get(role) or {})
    for key in ("temperature", "top_p", "max_tokens", "reasoning_effort"):
        if key in kwargs and kwargs[key] is not None:
            bucket[key] = kwargs[key]
    data.setdefault("sampling_overrides", {})[role] = bucket
    _save_overrides(data)
    log_system_action("override.sampling.set", f"{role}={bucket}")


def reset_sampling_override(role_key: str | None = None) -> None:
    data = _load_overrides()
    if role_key:
        data.setdefault("sampling_overrides", {}).pop(str(role_key).upper(), None)
    else:
        data["sampling_overrides"] = {}
    _save_overrides(data)
    log_system_action("override.sampling.reset", str(role_key or "ALL"))


__all__ = [
    "load_cli_settings",
    "get_cli_settings",
    "save_cli_settings",
    "log_system_action",
    "load_context_state",
    "save_context_state",
    "update_context_state",
    "is_context_active",
    "get_model_overrides",
    "set_model_override",
    "reset_model_override",
    "get_prompt_overrides",
    "set_prompt_override",
    "reset_prompt_override",
    "reset_all_role_overrides",
    "get_sampling_overrides",
    "update_sampling_override",
    "reset_sampling_override",
]
