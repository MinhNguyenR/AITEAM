"""In-memory stream buffers, reasoning state, token counters, and leader action tracker."""
from __future__ import annotations

import threading
import time

# -- In-memory leader stream buffer -------------------------------------------
_STREAM_LOCK = threading.Lock()
_STREAM_BUFFER: str = ""
_STREAM_UPDATED_AT: float = 0.0
_LEADER_STREAM_MAX = 48_000

# -- In-memory reasoning/thinking stream buffer --------------------------------
_REASONING_LOCK = threading.Lock()
_REASONING_BUFFER: str = ""
_REASONING_ACTIVE: bool = False
_REASONING_DONE: bool = False
_REASONING_MAX = 48_000

# -- Real-time token tracking --------------------------------------------------
_TOKEN_LOCK = threading.Lock()
_STREAM_CHAR_COUNT: int = 0
_STREAM_PROMPT_TOKENS: int = 0
_STREAM_COMPLETION_TOKENS: int = 0

# -- Leader action tracker -----------------------------------------------------
_LEADER_ACTION_LOCK = threading.Lock()
_LEADER_ACTION: str = ""


def clear_leader_stream_buffer() -> None:
    global _STREAM_BUFFER, _STREAM_UPDATED_AT
    with _STREAM_LOCK:
        _STREAM_BUFFER = ""
        _STREAM_UPDATED_AT = 0.0
    reset_stream_token_counters()
    clear_leader_action()


def append_leader_stream_chunk(text: str) -> None:
    global _STREAM_BUFFER, _STREAM_UPDATED_AT
    if not text:
        return
    with _STREAM_LOCK:
        _STREAM_BUFFER = (_STREAM_BUFFER + text)[-_LEADER_STREAM_MAX:]
        _STREAM_UPDATED_AT = time.time()


def drain_leader_stream_buffer() -> str:
    global _STREAM_BUFFER
    with _STREAM_LOCK:
        result = _STREAM_BUFFER
        _STREAM_BUFFER = ""
        return result


def set_reasoning_active(active: bool) -> None:
    global _REASONING_ACTIVE, _REASONING_DONE
    with _REASONING_LOCK:
        if _REASONING_ACTIVE and not active:
            _REASONING_DONE = True
        _REASONING_ACTIVE = active


def is_reasoning_active() -> bool:
    with _REASONING_LOCK:
        return _REASONING_ACTIVE


def append_reasoning_chunk(text: str) -> None:
    global _REASONING_BUFFER
    if not text:
        return
    with _REASONING_LOCK:
        _REASONING_BUFFER = (_REASONING_BUFFER + text)[-_REASONING_MAX:]


def drain_reasoning_buffer() -> tuple[str, bool, bool]:
    global _REASONING_BUFFER, _REASONING_DONE
    with _REASONING_LOCK:
        chunk = _REASONING_BUFFER
        _REASONING_BUFFER = ""
        active = _REASONING_ACTIVE
        ended = _REASONING_DONE
        _REASONING_DONE = False
        return chunk, active, ended


def clear_reasoning_buffer() -> None:
    global _REASONING_BUFFER, _REASONING_ACTIVE, _REASONING_DONE
    with _REASONING_LOCK:
        _REASONING_BUFFER = ""
        _REASONING_ACTIVE = False
        _REASONING_DONE = False


def increment_stream_char_count(n: int) -> None:
    global _STREAM_CHAR_COUNT
    with _TOKEN_LOCK:
        _STREAM_CHAR_COUNT += n


def get_stream_char_count() -> int:
    with _TOKEN_LOCK:
        return _STREAM_CHAR_COUNT


def set_stream_prompt_tokens(n: int) -> None:
    global _STREAM_PROMPT_TOKENS
    with _TOKEN_LOCK:
        if n > _STREAM_PROMPT_TOKENS:
            _STREAM_PROMPT_TOKENS = n


def get_stream_prompt_tokens() -> int:
    with _TOKEN_LOCK:
        return _STREAM_PROMPT_TOKENS


def set_stream_completion_tokens(n: int) -> None:
    global _STREAM_COMPLETION_TOKENS
    with _TOKEN_LOCK:
        if n > _STREAM_COMPLETION_TOKENS:
            _STREAM_COMPLETION_TOKENS = n


def get_stream_completion_tokens() -> int:
    with _TOKEN_LOCK:
        if _STREAM_COMPLETION_TOKENS > 0:
            return _STREAM_COMPLETION_TOKENS
        return _STREAM_CHAR_COUNT // 4


def reset_stream_token_counters() -> None:
    global _STREAM_CHAR_COUNT, _STREAM_PROMPT_TOKENS, _STREAM_COMPLETION_TOKENS
    with _TOKEN_LOCK:
        _STREAM_CHAR_COUNT = 0
        _STREAM_PROMPT_TOKENS = 0
        _STREAM_COMPLETION_TOKENS = 0


def set_leader_action(action: str) -> None:
    global _LEADER_ACTION
    with _LEADER_ACTION_LOCK:
        _LEADER_ACTION = str(action or "")


def get_leader_action() -> str:
    with _LEADER_ACTION_LOCK:
        return _LEADER_ACTION


def clear_leader_action() -> None:
    global _LEADER_ACTION
    with _LEADER_ACTION_LOCK:
        _LEADER_ACTION = ""


__all__ = [
    "clear_leader_stream_buffer", "append_leader_stream_chunk", "drain_leader_stream_buffer",
    "set_reasoning_active", "is_reasoning_active",
    "append_reasoning_chunk", "drain_reasoning_buffer", "clear_reasoning_buffer",
    "increment_stream_char_count", "get_stream_char_count",
    "set_stream_prompt_tokens", "get_stream_prompt_tokens",
    "set_stream_completion_tokens", "get_stream_completion_tokens",
    "reset_stream_token_counters",
    "set_leader_action", "get_leader_action", "clear_leader_action",
    # expose mutable state for get_pipeline_snapshot read access
    "_STREAM_BUFFER", "_STREAM_UPDATED_AT",
]
