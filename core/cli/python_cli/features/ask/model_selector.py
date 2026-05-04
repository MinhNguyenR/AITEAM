from __future__ import annotations

from agents._api_client import make_openai_client

from core.cli.python_cli.shell.state import log_system_action
from core.config import config
from core.config.settings import openrouter_base_url
from utils.budget_guard import ensure_dashboard_budget_available


def _chat_model_settings(mode: str) -> tuple[str, int, float, float]:
    from core.cli.python_cli.shell.state import get_sampling_overrides

    worker_id = "CHAT_MODEL_THINKING" if mode == "thinking" else "CHAT_MODEL_STANDARD"
    cfg = config.get_worker(worker_id) or {}
    samp = get_sampling_overrides().get(worker_id.upper(), {}) or {}
    model = str(cfg.get("model") or (config.ASK_CHAT_THINKING_MODEL if mode == "thinking" else config.ASK_CHAT_STANDARD_MODEL))
    if "max_tokens" in samp:
        max_tokens = int(samp["max_tokens"])
    else:
        max_tokens = int(cfg.get("max_tokens") or 1200)
    if "temperature" in samp:
        temperature = float(samp["temperature"])
    else:
        temperature = float(cfg.get("temperature") if cfg.get("temperature") is not None else 1.2)
    if "top_p" in samp:
        top_p = float(samp["top_p"])
    else:
        top_p = float(cfg.get("top_p") if cfg.get("top_p") is not None else 0.95)
    return model, max_tokens, temperature, top_p


def _ask_model(mode: str, messages: list[dict]) -> str:
    model, max_tokens, temperature, top_p = _chat_model_settings(mode)
    ensure_dashboard_budget_available()
    client = make_openai_client(config.api_key, openrouter_base_url())
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
    )
    content = (resp.choices[0].message.content or "").strip()
    usage = getattr(resp, "usage", None)
    prompt_tok = int(getattr(usage, "prompt_tokens", 0) or 0)
    completion_tok = int(getattr(usage, "completion_tokens", 0) or 0)
    if prompt_tok or completion_tok:
        try:
            from utils.tracker import append_usage_log, compute_cost_usd

            event = {
                "agent": "Ask",
                "model": model,
                "prompt_tokens": prompt_tok,
                "completion_tokens": completion_tok,
                "total_tokens": prompt_tok + completion_tok,
            }
            event["cost_usd"] = compute_cost_usd(event)
            append_usage_log(event)
        except (OSError, ValueError) as e:
            log_system_action("ask.usage_log_skipped", str(e))
    log_system_action("ask.response", f"model={model} chars={len(content)} token_limit={max_tokens}")
    return content
