from __future__ import annotations

import json
import sys
import time

from aiteamruntime.core.events import AgentEvent
from aiteamruntime.core.runtime import AgentContext, WorkItem

from ..config import WORKER_REGISTRY
from ..model import chat_completion, real_model_enabled, role_key
from ..utils import model_error, sleep


def worker_agent(ctx: AgentContext, event: AgentEvent) -> None:
    if event.agent_id != "Leader" or str(event.payload.get("dispatch_authority") or "") != "Leader":
        ctx.emit(
            "blocked",
            {
                "reason": "worker requires official Leader dispatch",
                "source_agent_id": event.agent_id,
                "work_item_id": event.work_item_id or str((event.payload or {}).get("work_item_id") or ""),
            },
            status="blocked",
            stage="work",
            work_item_id=event.work_item_id or str((event.payload or {}).get("work_item_id") or ""),
            role_state="blocked",
        )
        return
    item = WorkItem.from_payload(dict(event.assignment or event.payload.get("work_item") or event.payload))
    allowed = set(item.allowed_paths)
    started = time.monotonic()
    ctx.emit("reading", {"files": sorted(allowed), "work_item_id": item.id}, stage="work", work_item_id=item.id, role_state="running")
    sleep(0.02)
    target = sorted(allowed)[0] if allowed else f"virtual/{item.id}.txt"
    if not real_model_enabled():
        ctx.emit(
            "worker_failed",
            {"reason": "OPENROUTER_API_KEY is required for production worker execution", "work_item_id": item.id, "target": target},
            status="error",
            stage="work",
            work_item_id=item.id,
            role_state="error",
        )
        return
    resolved_role_key = role_key(ctx.agent_id)
    try:
        content = chat_completion(
            role_key=resolved_role_key,
            system=(
                "You are a worker agent in a real event-driven runtime test. "
                "Do exactly the assigned work item. Produce a concrete markdown/text artifact. "
                "Include lines starting with Agent:, Work item:, and RESULT:. "
                "Do not claim to modify files other than the assigned allowed path."
            ),
            user=json.dumps(
                {
                    "agent": ctx.agent_id,
                    "worker_role": WORKER_REGISTRY.get(ctx.agent_id, {}),
                    "work_item": item.to_dict(),
                    "target_file": target,
                },
                ensure_ascii=False,
                indent=2,
            ),
            max_tokens=900,
        )
    except Exception as exc:
        model_error(ctx, stage="work", exc=exc, work_item_id=item.id)
        ctx.emit("worker_failed", {"reason": str(exc), "work_item_id": item.id, "target": target}, status="error", stage="work", work_item_id=item.id)
        return
    ctx.emit("writing", {"file": target, "content": content, "work_item_id": item.id}, stage="work", work_item_id=item.id)
    try:
        full_path = ctx.runtime.resources.resolve_workspace_path(ctx.run_id, target)
        full_path.parent.mkdir(parents=True, exist_ok=True)
        before = full_path.read_text(encoding="utf-8").splitlines() if full_path.exists() else []
        full_path.write_text(content, encoding="utf-8")
        after = full_path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        ctx.emit("worker_failed", {"reason": str(exc), "work_item_id": item.id, "target": target}, status="error", stage="work", work_item_id=item.id)
        return
    ctx.emit("file_update", {"path": target, "absolute_path": str(full_path), "added_lines": max(0, len(after) - len(before)), "removed_lines": 0, "work_item_id": item.id}, stage="work", work_item_id=item.id)
    code = f"from pathlib import Path; p=Path({str(full_path)!r}); print('validated {item.id}:', p.exists(), p.stat().st_size)"
    ctx.emit(
        "terminal_requested",
        {
            "command": f"python validate workspace artifact {item.id}",
            "argv": [sys.executable, "-c", code],
            "cwd": ".",
            "work_item_id": item.id,
            "stage": "validate",
        },
        stage="validate",
        work_item_id=item.id,
    )
    ctx.emit("done", {"stage": "work", "work_item_id": item.id, "files_changed": [target]}, stage="work", work_item_id=item.id, duration_ms=int((time.monotonic() - started) * 1000), role_state="done")
