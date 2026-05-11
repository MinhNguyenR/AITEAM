from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path


class PipelineRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.path = root / "pipelines.json"
        self._lock = threading.RLock()
        self._pipelines: dict[str, dict] = {
            "trackaiteam": {
                "pipeline_id": "trackaiteam",
                "name": "trackaiteam",
                "workspace": "",
                "created_at": time.time(),
                "updated_at": time.time(),
            }
        }
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, list):
            return
        with self._lock:
            for item in data:
                if not isinstance(item, dict):
                    continue
                pipeline_id = str(item.get("pipeline_id") or "")
                if not pipeline_id:
                    continue
                self._pipelines[pipeline_id] = {
                    "pipeline_id": pipeline_id,
                    "name": str(item.get("name") or pipeline_id),
                    "workspace": str(item.get("workspace") or ""),
                    "created_at": float(item.get("created_at") or time.time()),
                    "updated_at": float(item.get("updated_at") or time.time()),
                }

    def _save(self) -> None:
        with self._lock:
            data = list(self._pipelines.values())
            self.root.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def list_pipelines(self, runs: list[dict] | None = None) -> list[dict]:
        with self._lock:
            items = {key: dict(item) for key, item in self._pipelines.items()}
        for run in runs or []:
            meta = run.get("metadata") or {}
            pipeline_id = str(meta.get("pipeline_id") or "trackaiteam")
            item = items.setdefault(
                pipeline_id,
                {
                    "pipeline_id": pipeline_id,
                    "name": pipeline_id,
                    "workspace": "",
                    "created_at": run.get("started_at") or run.get("updated_at") or time.time(),
                    "updated_at": run.get("updated_at") or time.time(),
                },
            )
            if meta.get("workspace") and not item.get("workspace"):
                item["workspace"] = str(meta.get("workspace") or "")
            item["updated_at"] = max(float(item.get("updated_at") or 0), float(run.get("updated_at") or 0))
        return sorted(items.values(), key=lambda item: float(item.get("created_at") or 0), reverse=False)

    def get_pipeline(self, pipeline_id: str) -> dict | None:
        with self._lock:
            item = self._pipelines.get(pipeline_id)
            return dict(item) if item is not None else None

    def create_pipeline(self, *, name: str, workspace: str = "") -> dict:
        now = time.time()
        pipeline_id = f"pipe-{uuid.uuid4().hex[:10]}"
        item = {
            "pipeline_id": pipeline_id,
            "name": name.strip() or "Untitled Pipeline",
            "workspace": workspace.strip(),
            "created_at": now,
            "updated_at": now,
        }
        with self._lock:
            self._pipelines[pipeline_id] = item
            self._save()
        return dict(item)

    def update_workspace(self, pipeline_id: str, workspace: str) -> None:
        with self._lock:
            item = self._pipelines.get(pipeline_id)
            if item is not None:
                item["workspace"] = workspace
                item["updated_at"] = time.time()
                self._save()

    def update_pipeline(self, pipeline_id: str, *, name: str = "", workspace: str = "") -> dict | None:
        with self._lock:
            item = self._pipelines.get(pipeline_id)
            if item is None:
                return None
            if name.strip():
                item["name"] = name.strip()
            if workspace.strip():
                item["workspace"] = workspace.strip()
            item["updated_at"] = time.time()
            self._save()
            return dict(item)
