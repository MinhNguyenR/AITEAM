from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any

from utils.file_manager import ensure_workflow_dir

_SESSION_LOCK = threading.Lock()


def session_file() -> Path:
    return ensure_workflow_dir() / "workflow_session.json"


def load_session_data(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_session_data(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, indent=2, ensure_ascii=False)
    with _SESSION_LOCK:
        tmp = path.with_name(path.name + ".tmp")
        for attempt in range(4):
            try:
                tmp.write_text(payload, encoding="utf-8")
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt < 3:
                    time.sleep(0.05 * (attempt + 1))
        try:
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, path)
        except OSError:
            path.write_text(payload, encoding="utf-8")
