"""Usage log JSONL: append, read, cost computation."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from utils.tracker_cache import cache_get, cache_set, invalidate_cache
from utils.tracker_helpers import (
    log_path,
    normalize_iso,
    parse_usage_timestamp,
    read_last_n_line_strings,
    safe_float,
    safe_int,
)

logger = logging.getLogger(__name__)


def _get_model_price_per_million(model_id: str, event: Dict[str, Any]) -> tuple[float, float]:
    pin = event.get("price_input_m")
    pout = event.get("price_output_m")
    if pin is not None and pout is not None:
        return safe_float(pin), safe_float(pout)
    try:
        from core.config import config

        p = config.get_live_pricing(model_id)
        return safe_float(p.get("input", 0.0)), safe_float(p.get("output", 0.0))
    except (ImportError, AttributeError, TypeError, ValueError):
        return 0.0, 0.0


def compute_cost_usd(event: Dict[str, Any]) -> float:
    prompt_tokens = safe_int(event.get("prompt_tokens"))
    completion_tokens = safe_int(event.get("completion_tokens"))
    model_id = str(event.get("model", "") or "")
    in_price_m, out_price_m = _get_model_price_per_million(model_id, event)
    return (prompt_tokens * in_price_m + completion_tokens * out_price_m) / 1_000_000


def append_usage_log(entry: Dict[str, Any]) -> None:
    normalized = dict(entry)
    normalized["timestamp"] = normalize_iso(normalized.get("timestamp"))
    normalized["agent"] = str(normalized.get("agent", "unknown"))
    normalized["role_key"] = str(normalized.get("role_key", "") or "")
    normalized["model"] = str(normalized.get("model", ""))
    normalized["prompt_tokens"] = safe_int(normalized.get("prompt_tokens"))
    normalized["completion_tokens"] = safe_int(normalized.get("completion_tokens"))
    if "total_tokens" not in normalized:
        normalized["total_tokens"] = normalized["prompt_tokens"] + normalized["completion_tokens"]
    normalized["total_tokens"] = safe_int(normalized.get("total_tokens"))
    if "cost_usd" not in normalized:
        normalized["cost_usd"] = compute_cost_usd(normalized)
    normalized["cost_usd"] = safe_float(normalized.get("cost_usd"))

    try:
        with open(log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(normalized, ensure_ascii=False) + "\n")
        invalidate_cache("usage_")
        invalidate_cache("build_summary:")
    except (OSError, TypeError, ValueError) as e:
        logger.warning("[Tracker] append_usage_log failed: %s", e)


def read_usage_log(last_n: int = 5000) -> List[Dict[str, Any]]:
    p = log_path()
    if not p.exists():
        return []
    cache_key = f"usage_log:{p}:{last_n}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    try:
        lines = read_last_n_line_strings(p, last_n)
    except (OSError, UnicodeDecodeError, ValueError) as e:
        logger.warning("[Tracker] read_usage_log failed: %s", e)
        return []

    rows: List[Dict[str, Any]] = []
    for line in lines:
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        raw["timestamp"] = normalize_iso(raw.get("timestamp"))
        raw["agent"] = str(raw.get("agent", "unknown"))
        raw["role_key"] = str(raw.get("role_key", "") or "")
        raw["model"] = str(raw.get("model", ""))
        raw["prompt_tokens"] = safe_int(raw.get("prompt_tokens"))
        raw["completion_tokens"] = safe_int(raw.get("completion_tokens"))
        raw["total_tokens"] = safe_int(raw.get("total_tokens")) or (raw["prompt_tokens"] + raw["completion_tokens"])
        raw["cost_usd"] = safe_float(raw.get("cost_usd"))
        if raw["cost_usd"] <= 0:
            raw["cost_usd"] = compute_cost_usd(raw)
        rows.append(raw)
    return cache_set(cache_key, rows)


def read_usage_rows_timerange(since: datetime, until: datetime, last_n: int = 50000) -> List[Dict[str, Any]]:
    cache_key = f"usage_range:{since.isoformat()}:{until.isoformat()}:{last_n}"
    cached = cache_get(cache_key)
    if cached is not None:
        return cached
    rows = read_usage_log(last_n=last_n)
    out: List[Dict[str, Any]] = []
    for r in rows:
        dt = parse_usage_timestamp(str(r.get("timestamp", "")))
        if dt is None:
            continue
        if since <= dt <= until:
            out.append(r)
    out.sort(key=lambda x: parse_usage_timestamp(str(x.get("timestamp", ""))) or datetime.min)
    return cache_set(cache_key, out)
