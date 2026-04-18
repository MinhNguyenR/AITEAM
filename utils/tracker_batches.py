"""CLI batch markers correlated with usage rows."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from utils.tracker_cache import cache_get, cache_set, invalidate_cache
from utils.tracker_helpers import (
    batches_path,
    parse_usage_timestamp,
    read_last_n_line_strings,
    safe_float,
    safe_int,
    token_io_totals,
)
from utils.tracker_usage import read_usage_rows_timerange

logger = logging.getLogger(__name__)


def append_cli_batch(mode: str, prompt_preview: str) -> None:
    rec = {
        "kind": "cli_batch",
        "timestamp": datetime.now().isoformat(),
        "mode": str(mode)[:16],
        "prompt": str(prompt_preview)[:220],
    }
    try:
        with open(batches_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        invalidate_cache("cli_batches:")
    except OSError as e:
        logger.warning("[Tracker] append_cli_batch: %s", e)


def read_cli_batches_tail(last_n_lines: int = 3000) -> List[Dict[str, Any]]:
    p = batches_path()
    if not p.exists():
        return []
    cache_key = f"cli_batches:{p}:{last_n_lines}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    lines = read_last_n_line_strings(p, last_n_lines)
    out: List[Dict[str, Any]] = []
    for line in lines:
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("kind") != "cli_batch":
            continue
        out.append(o)
    out.sort(key=lambda x: parse_usage_timestamp(str(x.get("timestamp", ""))) or datetime.min)
    return cache_set(cache_key, out)


def summarize_tokens_by_cli_batches(
    since: datetime,
    until: datetime,
    *,
    usage_tail_n: int = 50000,
) -> List[Dict[str, Any]]:
    cache_key = f"cli_summary:{since.isoformat()}:{until.isoformat()}:{usage_tail_n}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    filtered: List[Dict[str, Any]] = []
    for b in read_cli_batches_tail(5000):
        t = parse_usage_timestamp(str(b.get("timestamp", "")))
        if t and since <= t <= until:
            filtered.append(b)
    if not filtered:
        return []
    rows_in = read_usage_rows_timerange(since, until, last_n=usage_tail_n)
    results: List[Dict[str, Any]] = []
    for i, b in enumerate(filtered):
        t0 = parse_usage_timestamp(str(b.get("timestamp", "")))
        if t0 is None:
            continue
        t0_eff = max(t0, since)
        if i + 1 < len(filtered):
            t1 = parse_usage_timestamp(str(filtered[i + 1].get("timestamp", "")))
        else:
            t1 = until + timedelta(seconds=1)
        if t1 is None:
            t1 = until + timedelta(seconds=1)
        chunk = [
            r
            for r in rows_in
            if (dt := parse_usage_timestamp(str(r.get("timestamp", "")))) is not None and t0_eff <= dt < t1
        ]
        by_model: Dict[str, Dict[str, int]] = {}
        by_role: Dict[str, Dict[str, int]] = {}
        for r in chunk:
            mid = str(r.get("model") or "(unknown)")
            role = str(r.get("role_key") or r.get("agent") or "unknown")
            if mid not in by_model:
                by_model[mid] = {"prompt_tokens": 0, "completion_tokens": 0, "requests": 0, "cost_usd": 0.0}
            if role not in by_role:
                by_role[role] = {"prompt_tokens": 0, "completion_tokens": 0, "requests": 0, "cost_usd": 0.0}
            pt = safe_int(r.get("prompt_tokens"))
            ct = safe_int(r.get("completion_tokens"))
            cost = safe_float(r.get("cost_usd"))
            for bucket in (by_model[mid], by_role[role]):
                bucket["prompt_tokens"] += pt
                bucket["completion_tokens"] += ct
                bucket["requests"] += 1
                bucket["cost_usd"] += cost
        results.append(
            {
                "batch_idx": len(results) + 1,
                "timestamp": b.get("timestamp"),
                "mode": b.get("mode"),
                "prompt": b.get("prompt", ""),
                "by_model": by_model,
                "by_role": by_role,
                "totals": token_io_totals(chunk),
                "cost_usd": sum(safe_float(r.get("cost_usd")) for r in chunk),
                "usage_rows": chunk,
            }
        )
    return cache_set(cache_key, results)
