from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from core.config.constants import ACTIONS_LOG_FILE
from utils.env_guard import redact_for_display


def _actions_log_path() -> Path:
    path = Path.home() / ".ai-team" / ACTIONS_LOG_FILE.name
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def log_system_action(action: str, detail: str = "") -> None:
    rec = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "detail": redact_for_display(detail),
    }
    path = _actions_log_path()
    try:
        is_new = not path.exists()
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if is_new and os.name != "nt":
            try:
                os.chmod(path, 0o600)
            except OSError:
                pass
    except OSError:
        pass


__all__ = ["log_system_action"]
