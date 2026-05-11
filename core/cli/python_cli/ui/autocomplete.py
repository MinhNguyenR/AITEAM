from __future__ import annotations

from typing import Iterable, Optional
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from core.cli.python_cli.i18n import t

# -- Command Registry ----------------------------------------------------------
# Maps context keys to lists of (cmd, desc_key) tuples.
# Every command here starts with '/' as per the unified requirement.

COMMAND_REGISTRY: dict[str, list[tuple[str, str]]] = {
    "main": [
        ("/chat",              "cmd.chat"),
        ("/status",            "cmd.status"),
        ("/info",              "cmd.info"),
        ("/dashboard",         "cmd.dashboard"),
        ("/settings",          "cmd.settings"),
        ("/help",              "cmd.help"),
        ("/workflow",          "cmd.workflow"),
        ("/explain @codebase", "cmd.explain_codebase"),
        ("/explain @file",     "cmd.explain_file"),
        ("/explainer @codebase", "cmd.explain_codebase"),
        ("/explainer @file",     "cmd.explain_file"),
        ("/back",              "cmd.back"),
        ("/exit",              "cmd.exit"),
        ("/shutdown",          "cmd.shutdown"),
    ],
    "dashboard_home": [
        ("/history",   "cmd.history"),
        ("/total",     "cmd.total"),
        ("/budget",    "cmd.budget"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "dashboard_history": [
        ("/open",      "cmd.open"),
        ("/export",    "cmd.export"),
        ("/export pdf", "cmd.export"),
        ("/export xlsx", "cmd.export"),
        ("/export txt", "cmd.export"),
        ("/days",      "dash.viewing_days"),
        ("/next",      "cmd.next"),
        ("/prev",      "cmd.prev"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "dashboard_total": [
        ("/next",      "cmd.next"),
        ("/prev",      "cmd.prev"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "dashboard_budget": [
        ("/daily",     "cmd.daily"),
        ("/monthly",   "cmd.monthly"),
        ("/yearly",    "cmd.yearly"),
        ("/reset",     "cmd.reset"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "budget_value": [
        ("/unlimited", "unit.unlimited"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "settings": [
        ("/auto-accept", "cmd.auto_accept"),
        ("/context-action", "cmd.context_act"),
        ("/external-terminal", "cmd.help_ext"),
        ("/language",  "cmd.lang"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "agent_detail": [
        ("/model",     "cmd.model"),
        ("/prompt",    "cmd.prompt"),
        ("/sampling",  "cmd.sampling"),
        ("/reset",     "cmd.reset"),
        ("/free",      "cmd.free"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "context_viewer": [
        ("/run",       "cmd.run"),
        ("/edit",      "cmd.edit"),
        ("/delete",    "cmd.delete"),
        ("/regenerate", "cmd.regenerate"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "ask_chat": [
        ("/open",      "cmd.open"),
        ("/create",    "unit.create"),
        ("/delete",    "cmd.delete"),
        ("/rename",    "unit.rename"),
        ("/next",      "cmd.next"),
        ("/prev",      "cmd.prev"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
        ("/shutdown",  "cmd.shutdown"),
    ],
    "ask_session_standard": [
        ("/thinking",  "cmd.mode_thinking"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
        ("/shutdown",  "cmd.shutdown"),
    ],
    "ask_session_thinking": [
        ("/standard",  "cmd.mode_standard"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
        ("/shutdown",  "cmd.shutdown"),
    ],
    "context_confirm": [
        ("/accept",    "cmd.accept"),
        ("/edit",      "cmd.edit"),
        ("/regenerate", "cmd.regenerate"),
        ("/back",      "cmd.back"),
        ("/delete",    "cmd.delete"),
        ("/exit",      "cmd.exit"),
    ],
    "start_mode": [
        ("/ask",       "cmd.ask_mode"),
        ("/agent",     "cmd.agent_mode"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "agent_list": [
        ("/enter",     "cmd.enter"),
        ("/open",      "cmd.open"),
        ("/check change", "cmd.check_change"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "status": [
        ("/edit workspace", "cmd.edit"),
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "help": [
        ("/back",      "cmd.back"),
        ("/exit",      "cmd.exit"),
    ],
    "monitor": [
        ("/ask",        "cmd.ask_usage"),
        ("/agent",      "cmd.agent_usage"),
        ("/btw",        "cmd.btw_note_hint"),
        ("/explainer",  "cmd.explain_file"),
        ("/check",      "cmd.check"),
        ("/accept",     "context.accepted"),
        ("/delete",     "context.deleted"),
        ("/log",        "cmd.history"),
        ("/info",       "cmd.info"),
        ("/skip",       "btw.skipped"),
        ("/clear all",  "cmd.clear_all"),
        ("/clear text", "cmd.clear_text"),
        ("/exit",       "cmd.exit"),
    ],
}

def get_popup_sections() -> list[tuple[str, list[tuple[str, str]]]]:
    """Legacy helper for the monitor TUI layout. Maps to the new registry with translated descriptions."""
    # We group them for the monitor's specific UI layout
    monitor_cmds = COMMAND_REGISTRY["monitor"]

    def _t_list(cmds):
        return [(c, t(dk)) for c, dk in cmds]

    return [
        ("mode",    _t_list([c for c in monitor_cmds if c[0] in ("/ask", "/agent")])),
        ("check",   _t_list([c for c in monitor_cmds if c[0] in ("/log", "/info", "/check")])),
        ("support", _t_list([c for c in monitor_cmds if c[0] in ("/btw", "/skip", "/explainer", "/restore")])),
        ("clear",   _t_list([c for c in monitor_cmds if c[0] in ("/clear all", "/clear text")])),
        ("global",  _t_list([c for c in monitor_cmds if c[0] in ("/exit",)])),
    ]


class ChoiceCompleter(Completer):
    """A generic completer that suggests slash commands based on a context key."""

    def __init__(self, context: str = "main", include_global: bool = True):
        self.context = context
        self.include_global = include_global

    def get_completions(self, document: Document, complete_event: Iterable) -> Iterable[Completion]:
        text = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        # Only trigger if the user typed '/' or is in the middle of a word that started with '/'
        if not text.endswith('/') and not word.startswith('/'):
            return

        q = word.lower()
        if text.endswith('/') and not word:
            q = '/'

        cmds = COMMAND_REGISTRY.get(self.context, [])

        for cmd, desc_key in cmds:
            if cmd.lower().startswith(q) or (q == '/' and cmd.startswith('/')):
                desc = t(desc_key)
                yield Completion(
                    cmd,
                    start_position=-len(q) if q != '/' else 0,
                    display=cmd,
                    display_meta=desc
                )
