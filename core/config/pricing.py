from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple

from core.config.constants import HTTP_JSON_MAX_BYTES


def fetch_openrouter_pricing(
    api_key: str,
    pricing_cache: Dict[str, Dict[str, float]],
    pricing_fetched: bool,
    logger,
    force: bool = False,
) -> Tuple[Dict[str, Dict[str, float]], bool]:
    if pricing_fetched and not force:
        return pricing_cache, pricing_fetched

    url = "https://openrouter.ai/api/v1/models"
    try:
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {api_key}", "HTTP-Referer": "https://github.com/ai-team-blueprint"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # nosec B310
            raw = resp.read(HTTP_JSON_MAX_BYTES + 1)
            if len(raw) > HTTP_JSON_MAX_BYTES:
                raise ValueError(f"response exceeds {HTTP_JSON_MAX_BYTES} byte cap")
            data = json.loads(raw.decode("utf-8"))

        for model_info in data.get("data", []):
            mid = model_info.get("id", "")
            price = model_info.get("pricing", {})
            try:
                inp = float(price.get("prompt", 0)) * 1_000_000
                out = float(price.get("completion", 0)) * 1_000_000
                pricing_cache[mid] = {"input": inp, "output": out}
            except (ValueError, TypeError):
                pass

        pricing_fetched = True
        logger.info(f"[Config] Fetched pricing for {len(pricing_cache)} models from OpenRouter")
    except urllib.error.URLError as e:
        logger.warning(f"[Config] Could not fetch OpenRouter pricing: {e} — using config values")
    except (urllib.error.URLError, json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning(f"[Config] Pricing fetch error: {e} — using config values")

    return pricing_cache, pricing_fetched


def _numeric_leaves(obj: Any, prefix: str = "") -> Dict[str, float]:
    out: Dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                try:
                    out[key] = float(v)
                except (TypeError, ValueError):
                    pass
            elif isinstance(v, dict):
                out.update(_numeric_leaves(v, key))
    return out


def _collect_benchmark_scores(m: Dict[str, Any]) -> Dict[str, float]:
    scores: Dict[str, float] = {}
    skip = {"id", "name", "description", "pricing", "top_provider", "per_request_limits", "architecture"}
    for key in ("benchmark", "benchmarks"):
        v = m.get(key)
        if isinstance(v, dict):
            scores.update(_numeric_leaves(v, str(key)))
    for k, v in m.items():
        if k in skip or k in ("benchmark", "benchmarks"):
            continue
        if isinstance(v, dict) and v:
            nums = [x for x in v.values() if isinstance(x, (int, float)) and not isinstance(x, bool)]
            if nums and len(nums) == len(v):
                for nk, nv in v.items():
                    if isinstance(nv, (int, float)):
                        scores[f"{k}.{nk}"] = float(nv)
    return scores


def _pick_first(obj: Dict[str, Any], keys: tuple[str, ...], default: Any = None) -> Any:
    for k in keys:
        if k in obj and obj.get(k) is not None:
            return obj.get(k)
    return default


def fetch_model_detail(api_key: str, model_id: str) -> Dict[str, Any]:
    """Fetch live metadata for a single model from OpenRouter. Returns {} on failure."""
    url = "https://openrouter.ai/api/v1/models"
    try:
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"Bearer {api_key}", "HTTP-Referer": "https://github.com/ai-team-blueprint"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:  # nosec B310
            raw = resp.read(HTTP_JSON_MAX_BYTES + 1)
            if len(raw) > HTTP_JSON_MAX_BYTES:
                return {}
            data = json.loads(raw.decode("utf-8"))
        for m in data.get("data", []):
            if m.get("id") == model_id:
                price = m.get("pricing", {})
                try:
                    inp = float(price.get("prompt", 0)) * 1_000_000
                    out = float(price.get("completion", 0)) * 1_000_000
                except (ValueError, TypeError):
                    inp = out = 0.0
                arch = m.get("architecture")
                known = {
                    "id",
                    "name",
                    "description",
                    "pricing",
                    "context_length",
                    "top_provider",
                    "per_request_limits",
                    "architecture",
                }
                extra_keys = [k for k in m.keys() if k not in known]
                top_provider = m.get("top_provider", {}) or {}
                max_completion = _pick_first(
                    top_provider,
                    ("max_completion_tokens", "max_output_tokens", "max_tokens", "max_completion"),
                    None,
                )
                moderation = _pick_first(
                    top_provider,
                    ("is_moderated", "moderation", "moderated", "supports_moderation"),
                    None,
                )
                context_length = _pick_first(
                    m,
                    ("context_length", "max_context_length", "context_window", "max_input_tokens"),
                    None,
                )
                return {
                    "id": m.get("id", ""),
                    "name": m.get("name", ""),
                    "description": m.get("description", "") or "",
                    "context_length": context_length,
                    "input_price_per_1m": inp,
                    "output_price_per_1m": out,
                    "top_provider": top_provider,
                    "per_request_limits": m.get("per_request_limits"),
                    "architecture": arch,
                    "max_completion": max_completion,
                    "moderation": moderation,
                    "benchmark_scores": _collect_benchmark_scores(dict(m)),
                    "extra_keys": extra_keys,
                }
        return {}
    except (urllib.error.URLError, json.JSONDecodeError, ValueError, TypeError):
        return {}


def sync_live_pricing(model_registry: Dict, live_prices: Dict[str, Dict[str, float]]) -> None:
    if not live_prices:
        return
    for _, cfg in model_registry.items():
        model_id = cfg.get("model")
        if model_id in live_prices:
            cfg["pricing"] = live_prices[model_id]
            cfg["pricing_source"] = "live"
        else:
            cfg["pricing_source"] = "config_fallback"
