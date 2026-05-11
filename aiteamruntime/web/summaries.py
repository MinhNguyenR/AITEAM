from __future__ import annotations

import time
import uuid


def summarize_events(events: list[dict]) -> dict:
    agents = sorted({str(e.get("agent_id") or "") for e in events if e.get("agent_id")})
    kinds: dict[str, int] = {}
    for event in events:
        kind = str(event.get("kind") or "")
        kinds[kind] = kinds.get(kind, 0) + 1
    return {
        "events": len(events),
        "agents": agents,
        "kinds": kinds,
        "errors": kinds.get("error", 0) + kinds.get("abort", 0),
        "latest_ts": max((float(e.get("ts") or 0) for e in events), default=0.0),
    }


def filter_events(events: list[dict], query: dict[str, list[str]]) -> list[dict]:
    agent = (query.get("agent") or [""])[0].lower()
    kind = (query.get("kind") or [""])[0].lower()
    try:
        after = int((query.get("after") or ["0"])[0] or 0)
    except ValueError:
        after = 0
    out = []
    for event in events:
        if after and int(event.get("sequence") or 0) <= after:
            continue
        if agent and agent not in str(event.get("agent_id") or "").lower():
            continue
        if kind and kind != str(event.get("kind") or "").lower():
            continue
        out.append(event)
    return out


def summarize_resources(events: list[dict]) -> dict:
    blocked = [event for event in events if event.get("kind") == "blocked"]
    terminals = [
        event
        for event in events
        if str(event.get("kind") or "").startswith("terminal_") or event.get("kind") in {"setup_requested", "setup_done"}
    ]
    files = [event for event in events if event.get("kind") in {"file_create", "file_update"}]
    return {
        "blocked": blocked,
        "terminal_events": terminals,
        "file_events": files,
    }


def summarize_assignments(events: list[dict]) -> list[dict]:
    assignments: dict[str, dict] = {}
    for event in events:
        if event.get("kind") not in {"assigned", "reassigned", "worker_failed", "done"}:
            continue
        payload = event.get("assignment") or (event.get("payload") or {}).get("work_item") or event.get("payload") or {}
        work_item_id = str(event.get("work_item_id") or payload.get("id") or payload.get("work_item_id") or "")
        if not work_item_id:
            continue
        row = assignments.setdefault(work_item_id, {"id": work_item_id})
        row.update({k: v for k, v in payload.items() if k in {"title", "assigned_worker", "allowed_paths", "attempt", "timeout", "depends_on"}})
        if event.get("kind") == "worker_failed":
            row["status"] = "failed"
        elif event.get("kind") == "done":
            row["status"] = "done"
        else:
            row["status"] = "assigned"
    return list(assignments.values())


def summarize_agents(events: list[dict]) -> list[dict]:
    by_agent: dict[str, dict] = {}
    for event in events:
        agent_id = str(event.get("agent_id") or "")
        if not agent_id:
            continue
        item = by_agent.setdefault(
            agent_id,
            {"agent_id": agent_id, "events": 0, "last_kind": "", "last_status": "", "last_ts": 0.0},
        )
        item["events"] += 1
        item["last_kind"] = event.get("kind") or ""
        item["last_status"] = event.get("status") or ""
        item["last_ts"] = max(float(item.get("last_ts") or 0), float(event.get("ts") or 0))
    return sorted(by_agent.values(), key=lambda item: item["agent_id"])


def next_pipeline_run_number(runs: list[dict], pipeline_id: str) -> int:
    highest = 0
    count = 0
    for run in runs:
        meta = run.get("metadata") or {}
        rid = str(meta.get("pipeline_id") or "trackaiteam")
        if rid != pipeline_id:
            continue
        count += 1
        try:
            highest = max(highest, int(meta.get("run_number") or 0))
        except (TypeError, ValueError):
            pass
    return max(highest, count) + 1


def new_run_id(pipeline_id: str, run_number: int) -> str:
    safe = "".join(ch.lower() if ch.isalnum() else "-" for ch in pipeline_id).strip("-") or "pipeline"
    safe = "-".join(part for part in safe.split("-") if part)[:32] or "pipeline"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    return f"{safe}-run-{run_number:03d}-{stamp}-{uuid.uuid4().hex[:6]}"
