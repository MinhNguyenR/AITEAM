from __future__ import annotations

from typing import Any

from .config import WORKER_REGISTRY
from .utils import safe_rel_path, slug


def worker_id(value: str) -> str:
    raw = str(value or "").strip()
    if raw in WORKER_REGISTRY:
        return raw
    normalized = raw.replace("_", " ").lower()
    for key in WORKER_REGISTRY:
        if key.lower() == normalized:
            return key
    return ""


def _dep_key(value: str) -> str:
    return " ".join(str(value or "").replace("_", " ").lower().split())


def dag_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    project_root = str(plan.get("project_root") or "app").replace("\\", "/").strip("/.") or "app"
    if project_root.startswith(".aiteamruntime") or ".." in project_root:
        project_root = "app"
    work_items: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    raw_items = [raw for raw in plan.get("work_items") or [] if isinstance(raw, dict)]
    dep_aliases: dict[str, str] = {}
    generated_ids: list[str] = []
    for index, raw in enumerate(raw_items):
        worker = worker_id(str(raw.get("assigned_worker") or ""))
        if not worker:
            worker = list(WORKER_REGISTRY)[index % len(WORKER_REGISTRY)]
        item_id = str(raw.get("id") or f"wi-{slug(worker)}")
        generated_ids.append(item_id)
        aliases = {
            item_id,
            str(raw.get("id") or ""),
            str(raw.get("title") or ""),
            str(raw.get("task") or ""),
        }
        for alias in aliases:
            key = _dep_key(alias)
            if key:
                dep_aliases[key] = item_id
    for index, raw in enumerate(raw_items):
        if not isinstance(raw, dict):
            continue
        worker = worker_id(str(raw.get("assigned_worker") or ""))
        if not worker:
            worker = list(WORKER_REGISTRY)[index % len(WORKER_REGISTRY)]
        item_id = generated_ids[index]
        deps: list[str] = []
        dropped_deps: list[str] = []
        for dep in raw.get("depends_on") or []:
            dep_text = str(dep)
            if not dep_text:
                continue
            dep_id = dep_aliases.get(_dep_key(dep_text))
            if dep_id and dep_id != item_id:
                deps.append(dep_id)
            else:
                dropped_deps.append(dep_text)
        group_id = str(raw.get("group_id") or f"group-{index + 1}")
        files = raw.get("allowed_paths") or raw.get("files") or []
        allowed_paths = [safe_rel_path(str(path), f"{project_root}/README.md") for path in files if str(path).strip()]
        if not allowed_paths:
            allowed_paths = [f"{project_root}/README.md"]
        groups.append({"id": group_id, "run_mode": str(raw.get("run_mode") or "sequential"), "depends_on": []})
        work_items.append(
            {
                "id": item_id,
                "title": str(raw.get("title") or item_id),
                "assigned_worker": worker,
                "allowed_paths": list(dict.fromkeys(allowed_paths)),
                "depends_on": deps,
                "dropped_depends_on": dropped_deps,
                "group_id": group_id,
                "timeout": float(raw.get("timeout") or 120),
                "acceptance": str(raw.get("acceptance") or "assigned files validate"),
            }
        )
    seen: dict[str, dict[str, Any]] = {}
    for group in groups:
        seen.setdefault(str(group["id"]), group)
    return {"version": 1, "project_root": project_root, "groups": list(seen.values()), "work_items": work_items}


def validate_dag(dag: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    items = [item for item in dag.get("work_items") or [] if isinstance(item, dict)]
    groups = {str(group.get("id") or "") for group in dag.get("groups") or [] if isinstance(group, dict)}
    ids: set[str] = set()
    for item in items:
        item_id = str(item.get("id") or "")
        if not item_id:
            errors.append("work item missing id")
        elif item_id in ids:
            errors.append(f"duplicate work item id: {item_id}")
        ids.add(item_id)
        if not worker_id(str(item.get("assigned_worker") or "")):
            errors.append(f"{item_id}: unknown worker")
        if not item.get("allowed_paths"):
            errors.append(f"{item_id}: missing allowed_paths")
        if str(item.get("group_id") or "") not in groups:
            errors.append(f"{item_id}: unknown group")
    for item in items:
        for dep in item.get("depends_on") or []:
            if str(dep) not in ids:
                errors.append(f"{item.get('id')}: missing dependency {dep}")
    return errors


def work_items_from_dag(dag: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in dag.get("work_items") or [] if isinstance(item, dict)]
