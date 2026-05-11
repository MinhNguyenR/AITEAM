from __future__ import annotations

from io import StringIO

from core.cli.python_cli.i18n import t
from core.cli.python_cli.ui.autocomplete import COMMAND_REGISTRY

_MAX_FOOTER_CMDS = 14
_MONITOR_GATE_CMDS = frozenset({"/accept", "/delete"})


def markup_to_ansi(markup: str, width: int = 120) -> str:
    if not markup:
        return ""
    from rich.console import Console as RichConsole

    sio = StringIO()
    RichConsole(
        file=sio,
        highlight=False,
        markup=True,
        width=width,
        force_terminal=True,
        no_color=False,
    ).print(markup, end="")
    return sio.getvalue()


def palette_footer_markup(context: str, gate_pending: bool = False) -> str:
    cmds: list[str] = []
    for c, _ in COMMAND_REGISTRY.get(context, []):
        if context == "monitor" and not gate_pending and c in _MONITOR_GATE_CMDS:
            continue
        cmds.append(c)
    if len(cmds) > _MAX_FOOTER_CMDS:
        compact = " . ".join(cmds[:_MAX_FOOTER_CMDS]) + " . ..."
    else:
        compact = " . ".join(cmds)
    return f"[dim]{compact}  .  {t('cmd.palette_hint')}[/dim]"
