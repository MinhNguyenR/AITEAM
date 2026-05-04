"""Inline ask handler (extracted from _commands_mixin)."""
from __future__ import annotations

import threading

from ..core._constants import _SPINNER
from core.cli.python_cli.i18n import t


def handle_ask_inline(app, question: str) -> None:
    app._write("")
    app._write(f"[bold #7aa2f7]{t('ui.user')}[/bold #7aa2f7]")
    app._write("[dim]────────────────[/dim]")
    words, curr, qchunks = question.split(), "", []
    for w in words:
        if len(curr) + len(w) + 1 > 100:
            qchunks.append(curr); curr = w
        else:
            curr = (curr + " " + w).strip()
    if curr: qchunks.append(curr)
    for i, qc in enumerate(qchunks):
        app._write(f"[#7aa2f7]>[/#7aa2f7] {qc}" if i == 0 else f"  {qc}")
    app._ask_thinking = True
    app._set_live(f"[dim]   [#888888]{_SPINNER[app._spin % len(_SPINNER)]}[/#888888] {t('unit.thinking')}[/dim]")
    app._scroll_offset = 0

    def _run() -> None:
        try:
            from core.cli.python_cli.features.ask.model_selector import _ask_model
            from core.domain.prompts import ASK_MODE_SYSTEM_PROMPT
            msgs  = [{"role": "system", "content": ASK_MODE_SYSTEM_PROMPT}]
            msgs.append({"role": "user", "content": question})
            reply = _ask_model("standard", msgs)
            chunks: list[str] = []
            for raw_line in reply.split("\n"):
                if not raw_line.strip():
                    chunks.append(""); continue
                words_l, curr_l = raw_line.split(), ""
                for w in words_l:
                    if len(curr_l) + len(w) + 1 > 100:
                        chunks.append(curr_l); curr_l = w
                    else:
                        curr_l = (curr_l + " " + w).strip()
                if curr_l:
                    chunks.append(curr_l)

            def _show():
                app._ask_thinking = False
                app._set_live("")
                app._write("")
                app._write(f"[bold #9ece6a]{t('ui.assistant')}[/bold #9ece6a]")
                app._write("[dim]────────────────[/dim]")
                first = True
                for chunk in chunks:
                    if not chunk:
                        app._write("")
                    elif first:
                        app._write(f"[bold #9ece6a]>[/bold #9ece6a] {chunk}")
                        first = False
                    else:
                        app._write(f"  {chunk}")
                app._write("")
                app._scroll_offset = 0
                if app._app: app._app.invalidate()

            app._safe_ui(_show)
        except Exception as e:
            def _err():
                app._ask_thinking = False
                app._write(f"[red]✗ {t('cmd.ask_error')}: {e}[/red]")
                if app._app: app._app.invalidate()
            app._safe_ui(_err)

    threading.Thread(target=_run, daemon=True).start()
