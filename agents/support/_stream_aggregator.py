"""Consumes an OpenRouter stream into (content, usage, clarif_answer) tuple."""
from __future__ import annotations

import json
import logging
import re
import time
from typing import Any, List, Optional

from ._api_transport import _extract_cache_tokens, _parse_think_tags

logger = logging.getLogger(__name__)


def aggregate_stream(
    stream: Any,
    *,
    agent_name: str,
    chunk_callback=None,
) -> tuple[str, int, int, int, int, Optional[str]]:
    """Drain *stream* and return (content, prompt_tok, completion_tok, cache_read, cache_write, clarif_answer).

    *clarif_answer* is set when the leader model emitted a clarification request; None otherwise.
    """
    parts: List[str] = []
    usage_prompt = 0
    usage_completion = 0
    usage_cache_read = 0
    usage_cache_write = 0
    _in_think = False
    _had_reasoning = False

    _ws = None
    try:
        from core.runtime import session as _ws_mod
        _ws = _ws_mod
    except LookupError:
        pass

    if _ws:
        try:
            _ws.reset_stream_token_counters()
        except Exception:
            pass

    for chunk in stream:
        if _ws:
            try:
                if _ws.is_pipeline_stop_requested():
                    break
            except Exception:
                pass
        u = getattr(chunk, "usage", None)
        if u:
            new_pt = int(getattr(u, "prompt_tokens", 0) or 0)
            new_ct = int(getattr(u, "completion_tokens", 0) or 0)
            new_cr, new_cw = _extract_cache_tokens(u)
            if new_pt > usage_prompt:
                usage_prompt = new_pt
                if _ws:
                    try:
                        _ws.set_stream_prompt_tokens(new_pt)
                    except Exception:
                        pass
            if new_ct > usage_completion:
                usage_completion = new_ct
                if _ws:
                    try:
                        _ws.set_stream_completion_tokens(new_ct)
                    except Exception:
                        pass
            if new_cr > usage_cache_read:
                usage_cache_read = new_cr
            if new_cw > usage_cache_write:
                usage_cache_write = new_cw
        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        reasoning_native = getattr(delta, "reasoning_content", None) or ""
        if reasoning_native and _ws:
            _had_reasoning = True
            try:
                if not _ws.is_reasoning_active():
                    _ws.set_reasoning_active(True)
                _ws.append_reasoning_chunk(reasoning_native)
            except Exception:
                logger.debug("[%s] reasoning_content routing failed", agent_name)

        content_delta = getattr(delta, "content", None) or ""
        if not content_delta:
            continue

        main_text, think_text, _in_think = _parse_think_tags(content_delta, _in_think)

        if think_text and _ws:
            _had_reasoning = True
            try:
                if not _ws.is_reasoning_active():
                    _ws.set_reasoning_active(True)
                _ws.append_reasoning_chunk(think_text)
            except Exception:
                logger.debug("[%s] think-tag routing failed", agent_name)

        if main_text:
            if _had_reasoning and _ws:
                try:
                    if _ws.is_reasoning_active():
                        _ws.set_reasoning_active(False)
                except Exception:
                    pass
                _had_reasoning = False

            parts.append(main_text)
            if _ws:
                try:
                    _ws.increment_stream_char_count(len(main_text))
                except Exception:
                    pass
            if chunk_callback is not None:
                try:
                    chunk_callback(main_text)
                except Exception as _cb_err:
                    logger.debug("[%s] Stream callback error: %s", agent_name, type(_cb_err).__name__)
            elif _ws:
                try:
                    _ws.append_leader_stream_chunk(main_text)
                except LookupError:
                    logger.debug("[%s] stream monitor not active, chunk dropped", agent_name)

    if _had_reasoning and _ws:
        try:
            _ws.set_reasoning_active(False)
        except Exception:
            pass

    full_content = "".join(parts).strip()
    clarif_answer: Optional[str] = None

    if _ws:
        stripped = full_content
        _clarif_triggered = False
        if stripped.startswith("{"):
            try:
                obj = json.loads(stripped)
                if obj.get("type") == "clarify":
                    qs = obj.get("questions", [])
                    if qs:
                        _ws.set_clarification(qs)
                        logger.info("[%s] clarification (JSON) triggered: %d questions", agent_name, len(qs))
                        _deadline = time.time() + 600
                        while _ws.is_clarification_pending() and time.time() < _deadline:
                            time.sleep(0.5)
                        clarif_answer = _ws.get_clarification_answer() or "__skip__"
                        _ws.clear_clarification()
                        full_content = ""
                        _clarif_triggered = True
            except Exception as _ce:
                logger.debug("[%s] JSON clarification parse: %s", agent_name, _ce)

        if not _clarif_triggered and "[CLARIFICATION]" in full_content:
            _clarif_re = re.compile(r'\[CLARIFICATION\]\s*(\{.*?\})\s*\[/CLARIFICATION\]', re.DOTALL)
            for _m in _clarif_re.finditer(full_content):
                try:
                    _cdata = json.loads(_m.group(1))
                    _q = _cdata.get("question", "")
                    _opts = _cdata.get("options", [])
                    if _q and _opts:
                        _ws.set_clarification([{"question": _q, "options": _opts}])
                        logger.info("[%s] clarification (tag) triggered: %s", agent_name, _q[:60])
                        _deadline = time.time() + 600
                        while _ws.is_clarification_pending() and time.time() < _deadline:
                            time.sleep(0.5)
                        clarif_answer = _ws.get_clarification_answer() or "__skip__"
                        _ws.clear_clarification()
                        break
                except Exception as _ce:
                    logger.debug("[%s] tag clarification parse: %s", agent_name, _ce)
            full_content = re.sub(
                r'\[CLARIFICATION\].*?\[/CLARIFICATION\]', '', full_content, flags=re.DOTALL
            ).strip()

    return full_content, usage_prompt, usage_completion, usage_cache_read, usage_cache_write, clarif_answer
