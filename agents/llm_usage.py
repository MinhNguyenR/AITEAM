"""Backward-compat shim — import from agents._api_client directly."""
from agents._api_client import (
    chat_completions_create,
    chat_completions_create_stream,
    log_usage_event,
)

__all__ = [
    "chat_completions_create",
    "chat_completions_create_stream",
    "log_usage_event",
]
