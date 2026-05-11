from __future__ import annotations

import os
import sqlite3
from pathlib import Path


def sqlite_busy_timeout_ms(default: int = 20_000) -> int:
    raw = os.getenv("AI_TEAM_SQLITE_BUSY_TIMEOUT_MS", "").strip()
    try:
        return max(1000, int(raw)) if raw else default
    except ValueError:
        return default


def connect_wal(path: str | Path, *, timeout: float | None = None, foreign_keys: bool = True) -> sqlite3.Connection:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    busy_ms = sqlite_busy_timeout_ms()
    conn = sqlite3.connect(str(db_path), timeout=timeout if timeout is not None else busy_ms / 1000.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.OperationalError as exc:
        if "readonly" not in str(exc).lower():
            conn.close()
            raise
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(f"PRAGMA busy_timeout={busy_ms}")
    if foreign_keys:
        conn.execute("PRAGMA foreign_keys=ON")
    return conn
