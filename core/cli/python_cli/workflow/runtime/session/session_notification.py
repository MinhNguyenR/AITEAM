"""Toast messages and pipeline notifications for workflow sessions."""

from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Any

from ._session_core import load_session, save_session

_TOAST_SECONDS = 3.0


def _get_toast_queue(s: dict[str, Any]) -> list[dict[str, Any]]:
    q = s.get("pipeline_toast_queue")
    if not isinstance(q, list):
        return []
    return [x for x in q if isinstance(x, dict)]


def set_pipeline_toast(msg: str, *, seconds: float = _TOAST_SECONDS) -> None:
    text = str(msg)[:500].strip()
    if not text:
        return
    s = load_session()
    q = _get_toast_queue(s)
    dur = max(0.5, float(seconds))
    now = time.time()
    if not q:
        q.append({"msg": text, "until": now + dur, "dur": dur})
    else:
        q.append({"msg": text, "until": 0.0, "dur": dur})
    s["pipeline_toast_queue"] = q[-50:]
    s["pipeline_toast"] = q[0].get("msg", "")
    s["pipeline_toast_until"] = float(q[0].get("until") or 0.0)
    save_session(s)


def get_pipeline_toast_text() -> str:
    s = load_session()
    q = _get_toast_queue(s)
    if not q:
        legacy = str(s.get("pipeline_toast") or "")
        until = float(s.get("pipeline_toast_until") or 0.0)
        if legacy and until > 0 and time.time() <= until:
            return legacy
        if legacy or until:
            s["pipeline_toast"] = ""
            s["pipeline_toast_until"] = 0.0
            save_session(s)
        return ""
    now = time.time()
    dirty = False
    while q:
        head = q[0]
        until = float(head.get("until") or 0.0)
        if until <= 0:
            dur = float(head.get("dur") or _TOAST_SECONDS)
            head["until"] = now + dur
            q[0] = head
            dirty = True
            break
        if now > until:
            q.pop(0)
            dirty = True
            continue
        break
    if not q:
        s["pipeline_toast_queue"] = []
        s["pipeline_toast"] = ""
        s["pipeline_toast_until"] = 0.0
        save_session(s)
        return ""
    head = q[0]
    if dirty:
        s["pipeline_toast_queue"] = q
        s["pipeline_toast"] = str(head.get("msg") or "")
        s["pipeline_toast_until"] = float(head.get("until") or 0.0)
        save_session(s)
    return str(head.get("msg") or "")


def push_pipeline_notification(
    title: str,
    body: str,
    kind: str,
    extra: dict[str, Any] | None = None,
) -> str:
    nid = str(uuid.uuid4())
    s = load_session()
    items = s.get("pipeline_notifications")
    if not isinstance(items, list):
        items = []
    items.append(
        {
            "id": nid,
            "title": str(title)[:200],
            "body": str(body)[:2000],
            "kind": kind,
            "extra": dict(extra or {}),
            "ts": time.time(),
        }
    )
    s["pipeline_notifications"] = items[-25:]
    save_session(s)
    try:
        short = str(title)[:180]
        if str(body or "").strip():
            short = f"{short} — {(str(body) or '')[:120]}"
        set_pipeline_toast(short, seconds=3.0)
    except OSError:
        pass
    return nid


def list_active_notifications() -> list[dict[str, Any]]:
    s = load_session()
    items = s.get("pipeline_notifications")
    dismissed = s.get("dismissed_notification_ids")
    if not isinstance(items, list):
        return []
    if not isinstance(dismissed, list):
        dismissed = []
    dis = {str(x) for x in dismissed}
    return [x for x in items if isinstance(x, dict) and str(x.get("id")) not in dis]


def dismiss_pipeline_notification(nid: str) -> None:
    s = load_session()
    d = s.get("dismissed_notification_ids")
    if not isinstance(d, list):
        d = []
    if nid not in d:
        d.append(nid)
    s["dismissed_notification_ids"] = d[-200:]
    save_session(s)


def prune_stale_pipeline_notifications() -> None:
    s = load_session()
    items = s.get("pipeline_notifications")
    if not isinstance(items, list):
        return
    d = s.get("dismissed_notification_ids")
    if not isinstance(d, list):
        d = []
    dis = {str(x) for x in d}
    changed = False
    for n in items:
        if not isinstance(n, dict):
            continue
        nid = str(n.get("id", ""))
        if not nid or nid in dis:
            continue
        extra = n.get("extra") if isinstance(n.get("extra"), dict) else {}
        kind = str(n.get("kind", ""))
        path = None
        if kind == "context_ready":
            path = extra.get("context_path")
        elif kind == "state_json_ready":
            path = extra.get("state_path")
        if not path:
            continue
        try:
            missing = not Path(path).is_file()
        except OSError:
            missing = True
        if missing:
            d.append(nid)
            changed = True
    if changed:
        s["dismissed_notification_ids"] = d[-200:]
        save_session(s)
