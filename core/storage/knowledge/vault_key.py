from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def _normalize_key(raw: str) -> str:
    return (raw or "").strip()


def _secure_chmod(path: Path) -> None:
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_or_create_vault_key(base_dir: Path) -> Optional[str]:
    key_file = Path(base_dir) / "vault.key"

    env_key = _normalize_key(os.environ.get("AI_TEAM_VAULT_KEY", ""))
    if env_key:
        return env_key

    try:
        if key_file.is_file():
            existing = _normalize_key(key_file.read_text(encoding="ascii"))
            if existing:
                return existing
    except (OSError, UnicodeDecodeError):
        pass

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        logger.warning(
            "cryptography not installed; vault will fall back to unencrypted storage"
        )
        return None

    try:
        base_dir.mkdir(parents=True, exist_ok=True)
        generated = Fernet.generate_key().decode("ascii")
        key_file.write_text(generated, encoding="ascii")
        _secure_chmod(key_file)
        logger.info("Auto-generated vault key at %s", key_file)
        return generated
    except OSError as e:
        logger.warning("Failed to persist vault key (%s); using ephemeral key", e)
        try:
            from cryptography.fernet import Fernet as _F

            return _F.generate_key().decode("ascii")
        except (ImportError, ValueError):
            return None


__all__ = ["load_or_create_vault_key"]
