from __future__ import annotations

_STRINGS = {
    "ask.explain_suffix": "\n\nAnswer in explain-only mode. Do not modify files.",
    "context.new_chat_err": "No active chat.",
    "ask.history_rule": "History",
    "ask.msg_too_long": "Message too long: {n}",
    "ask.msg_invalid": "Invalid message: {e}",
    "ask.mode_thinking": "Already in thinking mode.",
    "ask.mode_standard": "Already in standard mode.",
    "ask.agent_mode_hint": "This looks like a coding task; use start workflow for code changes.",
    "cmd.ask_error": "Ask error",
    "ask.chat_col": "Chat",
    "ask.chat_list_title": "Chats",
    "ask.msg_count": "{n} messages",
}


def t(key: str, **kwargs) -> str:
    text = _STRINGS.get(key, key)
    try:
        return text.format(**kwargs) if kwargs else text
    except Exception:
        return text


__all__ = ["t"]
