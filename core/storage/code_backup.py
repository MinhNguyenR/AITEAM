"""SQLite-backed code backup for Worker rollback."""
from __future__ import annotations

import sqlite3
import time
import os
from pathlib import Path

from core.bootstrap import REPO_ROOT

_DB_PATH = Path.home() / ".ai-team" / "code_backups.db"


def _db_path() -> Path:
    override = os.getenv("AI_TEAM_CODE_BACKUP_DB", "").strip()
    return Path(override).expanduser() if override else _DB_PATH


def _conn() -> sqlite3.Connection:
    db_path = _db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path), check_same_thread=False, timeout=10)
    con.execute("""
        CREATE TABLE IF NOT EXISTS code_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_uuid TEXT NOT NULL DEFAULT '',
            file_path TEXT NOT NULL,
            content   TEXT NOT NULL,
            backed_up_at REAL NOT NULL,
            project_root TEXT NOT NULL DEFAULT ''
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_backups_task ON code_backups(task_uuid)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_backups_filepath ON code_backups(file_path)")
    # Migration: add project_root column to existing tables that lack it
    try:
        con.execute("ALTER TABLE code_backups ADD COLUMN project_root TEXT NOT NULL DEFAULT ''")
        con.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    con.commit()
    return con


def backup_file(file_path: str, content: str, task_uuid: str = "", project_root: str = "") -> int:
    """Save file content before overwrite. Returns backup_id."""
    root_norm = str(Path(project_root).resolve()) if project_root else ""
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO code_backups(task_uuid, file_path, content, backed_up_at, project_root) VALUES (?,?,?,?,?)",
            (task_uuid, file_path, content, time.time(), root_norm),
        )
        return cur.lastrowid or 0


def restore_file(backup_id: int) -> tuple[str, str]:
    """Restore file from backup. Returns (file_path, content)."""
    with _conn() as con:
        row = con.execute(
            "SELECT file_path, content FROM code_backups WHERE id=?", (backup_id,)
        ).fetchone()
    if not row:
        raise ValueError(f"No backup with id={backup_id}")
    return row[0], row[1]


def _safe_restore_target(file_path: str, project_root: str) -> Path | None:
    """Resolve backup file_path under project_root; return None if it escapes."""
    from core.sandbox._path_guard import resolve_under_project_root
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    if Path(file_path).is_absolute():
        # Accept absolute paths only if they are already under root
        target = Path(file_path).resolve()
        try:
            target.relative_to(root)
            return target
        except ValueError:
            return None
    return resolve_under_project_root(root, file_path)


def restore_backup(backup_id: int, project_root: str = "") -> dict:
    """Restore a backup id to disk and return metadata."""
    file_path, content = restore_file(backup_id)
    target = _safe_restore_target(file_path, project_root)
    if target is None:
        raise ValueError(f"Backup {backup_id}: path '{file_path}' is outside project root — restore refused")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"backup_id": backup_id, "file_path": file_path, "restored_to": str(target)}


def list_backups(task_uuid: str) -> list[dict]:
    """List all backups for a task."""
    with _conn() as con:
        rows = con.execute(
            "SELECT id, file_path, backed_up_at FROM code_backups WHERE task_uuid=? ORDER BY backed_up_at DESC",
            (task_uuid,),
        ).fetchall()
    return [{"id": r[0], "file_path": r[1], "backed_up_at": r[2]} for r in rows]


def search_backups(query: str, limit: int = 20, project_root: str = "") -> list[dict]:
    """Token-efficient LIKE search across file paths and content.

    If *project_root* is given, results are filtered to that project only.
    Passing an empty *query* without a *project_root* is rejected to prevent
    accidental full-DB scans used in restore fast-paths.
    """
    raw_query = str(query or "").strip()
    if not raw_query and not project_root:
        return []
    q = f"%{raw_query}%"
    root_norm = str(Path(project_root).resolve()) if project_root else ""

    with _conn() as con:
        if root_norm:
            rows = con.execute(
                """SELECT id, task_uuid, file_path, backed_up_at,
                          substr(content, 1, 240) AS snippet
                   FROM code_backups
                   WHERE project_root = ?
                     AND (task_uuid LIKE ? OR file_path LIKE ? OR content LIKE ?)
                   ORDER BY backed_up_at DESC
                   LIMIT ?""",
                (root_norm, q, q, q, int(limit)),
            ).fetchall()
        else:
            rows = con.execute(
                """SELECT id, task_uuid, file_path, backed_up_at,
                          substr(content, 1, 240) AS snippet
                   FROM code_backups
                   WHERE task_uuid LIKE ? OR file_path LIKE ? OR content LIKE ?
                   ORDER BY backed_up_at DESC
                   LIMIT ?""",
                (q, q, q, int(limit)),
            ).fetchall()
    return [
        {
            "id": r[0],
            "task_uuid": r[1],
            "file_path": r[2],
            "backed_up_at": r[3],
            "snippet": r[4],
        }
        for r in rows
    ]


def get_backup_summary(task_uuid: str) -> dict:
    """Return compact task backup counts without loading full content."""
    with _conn() as con:
        row = con.execute(
            """SELECT COUNT(*), COUNT(DISTINCT file_path), MIN(backed_up_at), MAX(backed_up_at)
               FROM code_backups WHERE task_uuid=?""",
            (task_uuid,),
        ).fetchone()
    return {
        "task_uuid": task_uuid,
        "backup_count": int(row[0] or 0),
        "file_count": int(row[1] or 0),
        "first_backed_up_at": row[2],
        "last_backed_up_at": row[3],
    }


def get_file_content_snippet(backup_id: int, start_line: int, end_line: int) -> str:
    """Return a small line range from one backup."""
    _, content = restore_file(backup_id)
    lines = content.splitlines()
    start = max(1, int(start_line or 1))
    end = max(start, int(end_line or start))
    return "\n".join(f"{idx}: {line}" for idx, line in enumerate(lines[start - 1:end], start=start))


def rollback_task(task_uuid: str, project_root: str = "") -> int:
    """Restore all files for a task. Returns number of files restored."""
    root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
    with _conn() as con:
        rows = con.execute(
            """SELECT file_path, content FROM code_backups
               WHERE task_uuid=?
               ORDER BY backed_up_at DESC""",
            (task_uuid,),
        ).fetchall()
    seen: set[str] = set()
    restored = 0
    for file_path, content in rows:
        if file_path in seen:
            continue
        seen.add(file_path)
        target = _safe_restore_target(file_path, str(root))
        if target is None:
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            restored += 1
        except OSError:
            pass
    return restored


__all__ = [
    "backup_file",
    "get_backup_summary",
    "get_file_content_snippet",
    "list_backups",
    "restore_backup",
    "restore_file",
    "rollback_task",
    "search_backups",
]
