from __future__ import annotations

import re

from prompt_toolkit.lexers import Lexer

from .styles import PALETTE_CMD_BOLD

# One cyan segment: from '/' through end of slash-command token (rest of line unstyled).
_CMD_PREFIX_RE = re.compile(r"^/[\w-]*", re.IGNORECASE)


class CommandLexer(Lexer):
    def lex_document(self, document):
        lines = document.text.split("\n")

        def get_line(lineno: int):
            line = lines[lineno] if lineno < len(lines) else ""
            if not line.startswith("/"):
                return [("", line)]
            m = _CMD_PREFIX_RE.match(line)
            if not m:
                return [("", line)]
            end = m.end()
            out: list = [
                (PALETTE_CMD_BOLD, line[:end]),
                ("", line[end:]),
            ]
            return out

        return get_line
