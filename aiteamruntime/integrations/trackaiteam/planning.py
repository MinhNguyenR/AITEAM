from __future__ import annotations

import sys
from typing import Any

from .config import WORKER_REGISTRY
from .model import model_meta
from .utils import safe_rel_path, slug


def normalize_model_plan(task: str, model_plan: dict[str, Any], *, role_key: str) -> dict[str, Any]:
    """Keep model-authored planning while enforcing runtime safety boundaries."""
    task_slug = slug(task)
    raw_items = model_plan.get("work_items") if isinstance(model_plan.get("work_items"), list) else []
    work_items: list[dict[str, Any]] = []
    worker_count = len(WORKER_REGISTRY)
    for index in range(worker_count):
        raw = raw_items[index] if index < len(raw_items) and isinstance(raw_items[index], dict) else {}
        worker_label = list(WORKER_REGISTRY)[index]
        role_slug = slug(WORKER_REGISTRY[worker_label]["role"], f"worker-{index + 1}")
        fallback = f".aiteamruntime/{task_slug}/{role_slug}.md"
        raw_files = raw.get("files") if isinstance(raw.get("files"), list) else []
        file_path = safe_rel_path(str(raw_files[0]) if raw_files else "", fallback)
        raw_depends_on = raw.get("depends_on") if isinstance(raw.get("depends_on"), list) else []
        work_items.append(
            {
                "id": str(raw.get("id") or f"wi-{role_slug}"),
                "title": str(raw.get("title") or f"{worker_label}: {WORKER_REGISTRY[worker_label]['reason']}"),
                "files": [file_path],
                "depends_on": [str(dep) for dep in raw_depends_on],
                "timeout": float(raw.get("timeout") or 60),
            }
        )
    raw_dependencies = model_plan.get("dependencies") if isinstance(model_plan.get("dependencies"), list) else []
    return {
        "task": task,
        "work_items": work_items,
        "setup_commands": [],
        "validation_commands": [{"argv": [sys.executable, "-c", "print('aiteamruntime openrouter validation ok')"], "label": "python validation check"}],
        "files": sorted({path for item in work_items for path in item["files"]}),
        "dependencies": [str(dep) for dep in raw_dependencies],
        "model_plan": {
            "reasoning": str(model_plan.get("reasoning") or ""),
            **model_meta(role_key),
        },
    }
