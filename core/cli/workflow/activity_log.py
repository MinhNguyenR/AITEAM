"""Append-only JSONL workflow activity log for monitor panel and `log` command."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from utils.activity_badges import format_action_with_badge, human_text_for
from utils.file_manager import ensure_workflow_dir


def _log_path() -> Path:
    return ensure_workflow_dir() / "workflow_activity.log"


def append_workflow_activity(
    node: str,
    action: str,
    detail: Any = "",
    *,
    level: str = "info",
) -> None:
    detail_text: str
    if isinstance(detail, dict):
        parts = []
        for key in ("task_id", "producer_node", "filename", "path", "status"):
            value = detail.get(key)
            if value:
                parts.append(f"{key}={value}")
        detail_text = " ".join(parts)[:4000]
    else:
        detail_text = str(detail or "")[:4000]
    rec = {
        "ts": time.time(),
        "level": level,
        "node": node,
        "action": action,
        "detail": detail_text,
    }
    path = _log_path()
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except OSError:
        pass


def clear_workflow_activity_log() -> None:
    path = _log_path()
    try:
        path.write_text("", encoding="utf-8")
    except OSError:
        pass


def truncate_workflow_activity_from_ts(ts_start: float) -> None:
    path = _log_path()
    if not path.is_file():
        return
    kept: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                    ts = float(rec.get("ts") or 0.0)
                except (ValueError, TypeError, json.JSONDecodeError):
                    continue
                if ts < ts_start:
                    kept.append(json.dumps(rec, ensure_ascii=False))
        path.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
    except OSError:
        pass


def remove_workflow_activity(*, node: str | None = None, min_ts: float | None = None) -> None:
    path = _log_path()
    if not path.is_file():
        return
    kept: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    rec = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                rec_node = str(rec.get("node", ""))
                try:
                    rec_ts = float(rec.get("ts") or 0.0)
                except (TypeError, ValueError):
                    rec_ts = 0.0
                remove = True
                if node is not None and rec_node != node:
                    remove = False
                if min_ts is not None and rec_ts < min_ts:
                    remove = False
                if not remove:
                    kept.append(json.dumps(rec, ensure_ascii=False))
        path.write_text(("\n".join(kept) + ("\n" if kept else "")), encoding="utf-8")
    except OSError:
        pass


def list_recent_activity(*, limit: int = 200, min_ts: float | None = None) -> list[dict[str, Any]]:
    path = _log_path()
    if not path.is_file():
        return []
    lines: list[str] = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if min_ts is not None:
            try:
                ts = float(rec.get("ts") or 0.0)
            except (TypeError, ValueError):
                ts = 0.0
            if ts < min_ts:
                continue
        out.append(rec)
    return out[-limit:]


_NOISY_ACTIONS = {"node_complete", "stream tick"}
_SKIP_NODES = {"monitor", "user"}


def format_activity_lines(records: list[dict[str, Any]], needle: str = "") -> list[str]:
    n = needle.lower().strip()
    lines: list[str] = []
    for r in records:
        node = str(r.get("node", ""))
        if node.lower() in _SKIP_NODES:
            continue
        act = str(r.get("action", ""))
        if act in _NOISY_ACTIONS:
            continue
        det = str(r.get("detail", ""))
        ts = r.get("ts", 0)
        blob = f"{node} {act} {det}".lower()
        if n and n not in blob:
            continue
        tss = time.strftime("%H:%M:%S", time.localtime(float(ts))) if ts else "?"
        human = human_text_for(node, act, det)
        if human:
            lines.append(f"[dim]{tss}[/dim] {human}")
        else:
            action_text = format_action_with_badge(act)
            lines.append(f"[dim]{tss}[/dim] [bold]{node}[/bold] {action_text} [dim]{det}[/dim]")
    return lines


__all__ = [
    "append_workflow_activity",
    "clear_workflow_activity_log",
    "truncate_workflow_activity_from_ts",
    "remove_workflow_activity",
    "list_recent_activity",
    "format_activity_lines",
]
