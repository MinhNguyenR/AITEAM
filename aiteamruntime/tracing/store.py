from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from ..core.events import AgentEvent

logger = logging.getLogger(__name__)

_SECRET_RE = re.compile(
    r"(?i)(sk-[a-z0-9_-]+|api[_-]?key\s*=\s*[^ \n\r\t]+|authorization:\s*bearer\s+[^ \n\r\t]+)"
)
SCHEMA_VERSION = 1


def default_trace_root() -> Path:
    return writable_fallback_root()


def default_db_path() -> Path:
    return default_trace_root() / "runtime.sqlite"


def user_data_root() -> Path:
    base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
    if base:
        return Path(base) / "aiteamruntime"
    return Path.home() / ".aiteamruntime"


def writable_fallback_root() -> Path:
    for root in (user_data_root(), Path(tempfile.gettempdir()) / "aiteamruntime"):
        try:
            root.mkdir(parents=True, exist_ok=True)
            probe = root / ".write-test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink(missing_ok=True)
            return root
        except OSError:
            continue
    raise PermissionError("no writable aiteamruntime sqlite fallback directory")


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return _SECRET_RE.sub("[REDACTED]", value)
    if isinstance(value, dict):
        return {str(k): redact_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_payload(v) for v in value]
    return value


class SQLiteTraceStore:
    """SQLite-backed local trace store for aiteamruntime.

    This is the production local store. It persists run metadata, events, and
    pipeline records in one SQLite database so the local viewer can survive
    refreshes/restarts without relying on JSON index files.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        raw = Path(root) if root is not None else default_trace_root()
        if raw.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            self.db_path = raw
            self.root = raw.parent
        else:
            self.root = raw
            self.db_path = raw / "runtime.sqlite"
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = self._connect()
        try:
            self._init_schema()
        except sqlite3.DatabaseError:
            self._recover_corrupt_database()
        self._migrate_legacy_json()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _recover_corrupt_database(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass
        stamp = time.strftime("%Y%m%d-%H%M%S")
        for path in (self.db_path, self.db_path.with_name(self.db_path.name + "-journal"), self.db_path.with_name(self.db_path.name + "-wal"), self.db_path.with_name(self.db_path.name + "-shm")):
            if not path.exists():
                continue
            target = path.with_name(f"{path.name}.corrupt-{stamp}")
            try:
                path.replace(target)
            except OSError as exc:
                logger.warning("failed to move corrupt sqlite artifact %s: %s", path, exc)
        self._conn = self._connect()
        try:
            self._init_schema()
        except sqlite3.DatabaseError:
            fallback_root = writable_fallback_root()
            fallback = fallback_root / "runtime.sqlite"
            logger.warning("falling back to sqlite database %s", fallback)
            self.db_path = fallback
            self.root = fallback_root
            self._conn = self._connect()
            self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA user_version = %d" % SCHEMA_VERSION)
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    pipeline_id TEXT NOT NULL DEFAULT '',
                    run_name TEXT NOT NULL DEFAULT '',
                    task TEXT NOT NULL DEFAULT '',
                    workspace TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'running',
                    started_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    last_agent_id TEXT NOT NULL DEFAULT '',
                    last_kind TEXT NOT NULL DEFAULT '',
                    events INTEGER NOT NULL DEFAULT 0,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    stage TEXT NOT NULL DEFAULT '',
                    ts REAL NOT NULL,
                    payload_json TEXT NOT NULL DEFAULT '{}',
                    event_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, sequence),
                    UNIQUE (event_id)
                )
                """
            )
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, sequence)")
            self._conn.execute("CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind)")
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS pipelines (
                    pipeline_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    workspace TEXT NOT NULL DEFAULT '',
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            now = time.time()
            self._conn.execute(
                """
                INSERT OR IGNORE INTO pipelines(pipeline_id, name, workspace, created_at, updated_at)
                VALUES('trackaiteam', 'trackaiteam', '', ?, ?)
                """,
                (now, now),
            )

    @property
    def index_path(self) -> Path:
        return self.root / "index.json"

    def trace_path(self, run_id: str) -> Path:
        safe = "".join(ch for ch in str(run_id) if ch.isalnum() or ch in ("-", "_", "."))
        if not safe:
            raise ValueError("run_id is required")
        return self.root / f"{safe}.jsonl"

    def start_run(self, run_id: str, metadata: dict[str, Any] | None = None) -> None:
        meta = redact_payload(dict(metadata or {}))
        now = time.time()
        pipeline_id = str(meta.get("pipeline_id") or "")
        run_name = str(meta.get("run_name") or "")
        task = str(meta.get("task") or meta.get("prompt") or "")
        workspace = str(meta.get("workspace") or "")
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO runs(run_id, pipeline_id, run_name, task, workspace, status, started_at, updated_at, metadata_json)
                VALUES(?, ?, ?, ?, ?, 'running', ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    pipeline_id=excluded.pipeline_id,
                    run_name=excluded.run_name,
                    task=excluded.task,
                    workspace=excluded.workspace,
                    status='running',
                    updated_at=excluded.updated_at,
                    metadata_json=excluded.metadata_json
                """,
                (run_id, pipeline_id, run_name, task, workspace, now, now, json.dumps(meta, ensure_ascii=False)),
            )

    def append(self, event: AgentEvent) -> None:
        clean = event.to_dict()
        clean["payload"] = redact_payload(clean.get("payload") or {})
        payload_json = json.dumps(clean.get("payload") or {}, ensure_ascii=False, sort_keys=True)
        event_json = json.dumps(clean, ensure_ascii=False, sort_keys=True)
        status = self._status_for_event(clean)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT OR IGNORE INTO runs(run_id, started_at, updated_at, status, metadata_json)
                VALUES(?, ?, ?, 'running', '{}')
                """,
                (event.run_id, float(clean.get("ts") or time.time()), float(clean.get("ts") or time.time())),
            )
            self._conn.execute(
                """
                INSERT OR REPLACE INTO events(
                    run_id, sequence, event_id, agent_id, kind, status, stage, ts, payload_json, event_json
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    clean["run_id"],
                    int(clean.get("sequence") or 0),
                    clean["event_id"],
                    clean["agent_id"],
                    clean["kind"],
                    clean["status"],
                    clean.get("stage") or "",
                    float(clean.get("ts") or time.time()),
                    payload_json,
                    event_json,
                ),
            )
            self._conn.execute(
                """
                UPDATE runs
                SET updated_at=?, last_agent_id=?, last_kind=?, events=(
                    SELECT COUNT(*) FROM events WHERE run_id=?
                ), status=CASE WHEN ? != '' THEN ? ELSE status END
                WHERE run_id=?
                """,
                (
                    float(clean.get("ts") or time.time()),
                    clean["agent_id"],
                    clean["kind"],
                    clean["run_id"],
                    status,
                    status,
                    clean["run_id"],
                ),
            )

    def list_runs(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM runs
                ORDER BY started_at DESC
                LIMIT 500
                """
            ).fetchall()
        return [self._run_row(row) for row in rows]

    def read_events(self, run_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT event_json FROM events WHERE run_id=? ORDER BY sequence ASC",
                (run_id,),
            ).fetchall()
        return [json.loads(str(row["event_json"])) for row in rows]

    def tail_events(self, run_id: str, *, since_seq: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT event_json FROM events WHERE run_id=? AND sequence>? ORDER BY sequence ASC",
                (run_id, int(since_seq or 0)),
            ).fetchall()
        return [json.loads(str(row["event_json"])) for row in rows]

    def list_pipelines(self, runs: list[dict] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM pipelines ORDER BY created_at ASC",
            ).fetchall()
        items = {str(row["pipeline_id"]): dict(row) for row in rows}
        for run in runs or []:
            meta = run.get("metadata") or {}
            pipeline_id = str(meta.get("pipeline_id") or run.get("pipeline_id") or "trackaiteam")
            item = items.setdefault(
                pipeline_id,
                {
                    "pipeline_id": pipeline_id,
                    "name": pipeline_id,
                    "workspace": "",
                    "created_at": run.get("started_at") or time.time(),
                    "updated_at": run.get("updated_at") or time.time(),
                },
            )
            if meta.get("workspace") and not item.get("workspace"):
                item["workspace"] = str(meta.get("workspace") or "")
            item["updated_at"] = max(float(item.get("updated_at") or 0), float(run.get("updated_at") or 0))
        return sorted(items.values(), key=lambda item: float(item.get("created_at") or 0))

    def get_pipeline(self, pipeline_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM pipelines WHERE pipeline_id=?", (pipeline_id,)).fetchone()
        return dict(row) if row is not None else None

    def create_pipeline(self, *, name: str, workspace: str = "", pipeline_id: str = "") -> dict[str, Any]:
        if not pipeline_id:
            import uuid

            pipeline_id = f"pipe-{uuid.uuid4().hex[:10]}"
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO pipelines(pipeline_id, name, workspace, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?)
                """,
                (pipeline_id, name.strip() or pipeline_id, workspace.strip(), now, now),
            )
        return {
            "pipeline_id": pipeline_id,
            "name": name.strip() or pipeline_id,
            "workspace": workspace.strip(),
            "created_at": now,
            "updated_at": now,
        }

    def update_pipeline(self, pipeline_id: str, *, name: str = "", workspace: str = "") -> dict[str, Any] | None:
        current = self.get_pipeline(pipeline_id)
        if current is None:
            return None
        updated = {
            **current,
            "name": name.strip() or current["name"],
            "workspace": workspace.strip() or current["workspace"],
            "updated_at": time.time(),
        }
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE pipelines SET name=?, workspace=?, updated_at=? WHERE pipeline_id=?
                """,
                (updated["name"], updated["workspace"], updated["updated_at"], pipeline_id),
            )
        return updated

    def update_workspace(self, pipeline_id: str, workspace: str) -> None:
        self.update_pipeline(pipeline_id, workspace=workspace)

    def health(self) -> dict[str, Any]:
        with self._lock:
            version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        return {"backend": "sqlite", "root": str(self.root), "db_path": str(self.db_path), "schema_version": int(version)}

    def shutdown(self) -> None:
        with self._lock:
            self._conn.commit()

    def _run_row(self, row: sqlite3.Row) -> dict[str, Any]:
        try:
            metadata = json.loads(str(row["metadata_json"] or "{}"))
        except json.JSONDecodeError:
            metadata = {}
        return {
            "run_id": row["run_id"],
            "started_at": float(row["started_at"] or 0),
            "updated_at": float(row["updated_at"] or 0),
            "events": int(row["events"] or 0),
            "last_agent_id": row["last_agent_id"] or "",
            "last_kind": row["last_kind"] or "",
            "status": row["status"] or "running",
            "pipeline_id": row["pipeline_id"] or "",
            "run_name": row["run_name"] or "",
            "task": row["task"] or "",
            "workspace": row["workspace"] or "",
            "metadata": metadata,
        }

    def _status_for_event(self, event: dict[str, Any]) -> str:
        kind = str(event.get("kind") or "")
        status = str(event.get("status") or "")
        if kind in {"run_aborted", "abort"} or status == "aborted":
            return "aborted"
        if kind == "cleanup_complete":
            return "cleaned"
        if kind in {"run_finished", "finalized"}:
            return "finished"
        return ""

    def _migrate_legacy_json(self) -> None:
        legacy_index = self.root / "index.json"
        try:
            data = json.loads(legacy_index.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return
        items = data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        for item in items:
            if not isinstance(item, dict) or not item.get("run_id"):
                continue
            run_id = str(item["run_id"])
            meta = dict(item.get("metadata") or {})
            with self._lock, self._conn:
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO runs(
                        run_id, pipeline_id, run_name, task, workspace, status, started_at, updated_at,
                        last_agent_id, last_kind, events, metadata_json
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        run_id,
                        str(meta.get("pipeline_id") or ""),
                        str(meta.get("run_name") or ""),
                        str(meta.get("task") or meta.get("prompt") or ""),
                        str(meta.get("workspace") or ""),
                        str(item.get("status") or "finished"),
                        float(item.get("started_at") or item.get("updated_at") or time.time()),
                        float(item.get("updated_at") or item.get("started_at") or time.time()),
                        str(item.get("last_agent_id") or ""),
                        str(item.get("last_kind") or ""),
                        int(item.get("events") or 0),
                        json.dumps(meta, ensure_ascii=False),
                    ),
                )
            self._migrate_legacy_events(run_id)

    def _migrate_legacy_events(self, run_id: str) -> None:
        path = self.trace_path(run_id)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return
        for line in lines:
            try:
                data = json.loads(line)
                event = AgentEvent.from_dict(data)
            except Exception:
                continue
            self.append(event)


TraceStore = SQLiteTraceStore

__all__ = ["SQLiteTraceStore", "TraceStore", "default_trace_root", "default_db_path", "redact_payload"]
