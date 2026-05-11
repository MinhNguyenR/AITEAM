from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class ReferenceStore:
    """Stores lightweight reference metadata outside event payloads."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.db_path = self.root / "refs.sqlite"
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=20.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=20000")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS refs (
                    ref_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    path TEXT NOT NULL DEFAULT '',
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    content TEXT NULL,
                    created_at REAL NOT NULL
                )
                """
            )

    def create_file_ref(
        self,
        run_id: str,
        path: str,
        *,
        metadata: dict[str, Any] | None = None,
        content: str | None = None,
    ) -> str:
        ref_id = f"#FILE_{uuid.uuid4().hex[:12]}"
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO refs(ref_id, run_id, kind, path, metadata_json, content, created_at)
                VALUES (?, ?, 'file', ?, ?, ?, ?)
                """,
                (ref_id, run_id, str(path), json.dumps(metadata or {}, ensure_ascii=False), content, time.time()),
            )
        return ref_id

    def metadata(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT ref_id, kind, path, metadata_json, created_at FROM refs WHERE run_id = ? ORDER BY created_at",
                (run_id,),
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            try:
                item["metadata"] = json.loads(str(item.pop("metadata_json") or "{}"))
            except json.JSONDecodeError:
                item["metadata"] = {}
            out.append(item)
        return out

    def hydrate(self, run_id: str, ref_id: str, *, workspace: str = "") -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT ref_id, kind, path, metadata_json, content FROM refs WHERE run_id = ? AND ref_id = ?",
                (run_id, ref_id),
            ).fetchone()
        if row is None:
            raise KeyError(f"unknown ref: {ref_id}")
        item = dict(row)
        metadata = json.loads(str(item.get("metadata_json") or "{}"))
        content = item.get("content")
        path = str(item.get("path") or "")
        if content is None and path:
            full = Path(path)
            if workspace:
                root = Path(workspace).resolve()
                full = full if full.is_absolute() else root / path
                resolved = full.resolve()
                resolved.relative_to(root)
                full = resolved
            content = full.read_text(encoding="utf-8", errors="replace")
        return {"ref_id": ref_id, "kind": item.get("kind"), "path": path, "metadata": metadata, "content": content or ""}


__all__ = ["ReferenceStore"]
