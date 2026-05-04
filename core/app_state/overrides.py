from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config.constants import MODEL_OVERRIDES_FILE

from ._io import write_secure
from .actions import log_system_action

logger = logging.getLogger(__name__)
_crypto_warned = False


def _overrides_file() -> Path:
    return Path.home() / ".ai-team" / MODEL_OVERRIDES_FILE.name


def _load_overrides() -> dict:
    overrides_file = _overrides_file()
    if not overrides_file.exists():
        return {"model_overrides": {}, "prompt_overrides": {}, "sampling_overrides": {}}
    try:
        data = json.loads(overrides_file.read_text(encoding="utf-8"))
        data.setdefault("sampling_overrides", {})
        return data
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {"model_overrides": {}, "prompt_overrides": {}, "sampling_overrides": {}}


def _save_overrides(data: dict) -> None:
    write_secure(_overrides_file(), json.dumps(data, indent=2, ensure_ascii=False) + "\n")


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
    return {key: {**value, "prompt": _decrypt_prompt(value)} for key, value in raw.items()}


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
