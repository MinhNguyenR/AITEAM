"""Resilient JSON parsing utilities for LLM outputs.

Stdlib-only — no imports from agents or core.cli.python_cli.
"""

from __future__ import annotations

import json
import re


def strip_markdown_fences(content: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` code-fence wrappers."""
    content = re.sub(r"^```(?:json)?\n?", "", content.strip())
    content = re.sub(r"\n?```$", "", content)
    return content


def parse_json_resilient(content: str) -> dict:
    """Parse JSON from LLM output with three fallback strategies.

    1. Direct json.loads
    2. Regex extraction of first ``{...}`` block
    3. Fix trailing commas then retry

    Raises json.JSONDecodeError if all three strategies fail.
    """
    # Strategy 1 — direct parse
    try:
        return json.loads(content)
    except json.JSONDecodeError as original_err:
        pass  # try fallbacks

    # Strategy 2 — extract first {...} block
    match = re.search(r"\{[^{}]*\}", content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Strategy 3 — fix trailing commas
    fixed = re.sub(r",\s*}", "}", content)
    fixed = re.sub(r",\s*]", "]", fixed)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass

    raise json.JSONDecodeError(
        f"parse_json_resilient: all strategies failed",
        content,
        0,
    )


__all__ = ["strip_markdown_fences", "parse_json_resilient"]
