"""Input validation for user-supplied prompts at system boundaries."""

from __future__ import annotations

MAX_PROMPT_CHARS = 32_000


class PromptTooLong(ValueError):
    pass


class PromptInvalid(ValueError):
    pass


def validate_user_prompt(text: str) -> str:
    """Validate and return a cleaned user prompt.

    Raises PromptTooLong if text exceeds MAX_PROMPT_CHARS.
    Raises PromptInvalid if text is empty or contains null bytes.
    """
    if not isinstance(text, str):
        raise PromptInvalid("Prompt must be a string")
    cleaned = text.strip()
    if not cleaned:
        raise PromptInvalid("Prompt cannot be empty")
    if "\x00" in cleaned:
        raise PromptInvalid("Prompt contains null bytes")
    if len(cleaned) > MAX_PROMPT_CHARS:
        raise PromptTooLong(
            f"Prompt is {len(cleaned):,} characters; maximum is {MAX_PROMPT_CHARS:,}"
        )
    return cleaned


__all__ = ["validate_user_prompt", "PromptTooLong", "PromptInvalid", "MAX_PROMPT_CHARS"]
