"""Backward-compat shim — import from core.domain.delta_brief directly."""
from core.domain.delta_brief import (
    CONTEXT_FILENAME,
    DeltaBrief,
    NO_CONTEXT_HEADER,
    STATE_FILENAME,
    VALIDATION_REPORT_FILENAME,
    build_state_payload,
    is_no_context,
)

__all__ = [
    "CONTEXT_FILENAME",
    "DeltaBrief",
    "NO_CONTEXT_HEADER",
    "STATE_FILENAME",
    "VALIDATION_REPORT_FILENAME",
    "build_state_payload",
    "is_no_context",
]
