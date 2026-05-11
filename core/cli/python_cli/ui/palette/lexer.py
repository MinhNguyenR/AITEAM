from __future__ import annotations

import re
from typing import Callable, List, Optional

from prompt_toolkit.lexers import Lexer

from .styles import PALETTE_CMD_BOLD

# Fallback regexes if get_valid_items is not provided
_CMD_PREFIX_RE = re.compile(r"^/[\w-]+", re.IGNORECASE)
_AT_PREFIX_RE = re.compile(r"^@[\w\-\.\/\\]*", re.IGNORECASE)

class CommandLexer(Lexer):
    def __init__(self, get_valid_items: Optional[Callable[[], List[str]]] = None):
        self.get_valid_items = get_valid_items

    def lex_document(self, document):
        lines = document.text.split("\n")

        def get_line(lineno: int):
            line = lines[lineno] if lineno < len(lines) else ""
            if not line.startswith("/") and not line.startswith("@"):
                return [("", line)]

            end = 0
            valid_items: list[str] = []
            if self.get_valid_items:
                valid_items = self.get_valid_items()
            elif line.startswith("/"):
                try:
                    from core.cli.python_cli.ui.autocomplete import COMMAND_REGISTRY

                    seen: set[str] = set()
                    for rows in COMMAND_REGISTRY.values():
                        for cmd, _desc_key in rows:
                            seen.add(cmd)
                    valid_items = sorted(seen)
                except Exception:
                    valid_items = []

            if valid_items:
                # Find the longest valid item that matches the start of the line (case insensitive)
                lower_line = line.lower()
                for item in sorted(valid_items, key=len, reverse=True):
                    if lower_line.startswith(item.lower()):
                        # Check if the matched item is a full word or followed by space
                        # to avoid matching "/check" when user typed "/checkmate" (if checkmate is not valid)
                        # Wait, command strings might contain spaces like "/check change".
                        item_len = len(item)
                        if item_len == len(line) or line[item_len].isspace():
                            end = item_len
                            break

            if end == 0:
                if self.get_valid_items is None:
                    # Fallback to the first slash token only if no registry item matched.
                    if line.startswith("/"):
                        m = _CMD_PREFIX_RE.match(line)
                        if m:
                            end = m.end()
                    elif line.startswith("@"):
                        m = _AT_PREFIX_RE.match(line)
                        if m:
                            end = m.end()

            if end == 0:
                return [("", line)]

            return [
                (PALETTE_CMD_BOLD, line[:end]),
                ("", line[end:]),
            ]

        return get_line
