"""Inline btw handler (extracted from _commands_mixin)."""
from __future__ import annotations

import threading
import time

from ..core._constants import _GEN_STEPS, _SPINNER
from core.cli.python_cli.i18n import t


def handle_btw_inline(app, msg: str, snap: dict) -> None:
    active = str(snap.get("active_step") or "idle")
    tier   = snap.get("brief_tier")

    # The AI will decide if the message is a stop command by emitting [STOP_WORKFLOW]

    raw_lines     = msg.strip().split("\n")
    disp_lines    = raw_lines[:12]
    was_truncated = len(raw_lines) > 12
    from ..core._utils import _get_role_display
    role_name = _get_role_display(active) if active in _GEN_STEPS else _get_role_display("leader_generate")
    try:
        from ..helpers import _model_for_step
        model_short = _model_for_step(active, tier) or "leader"
    except Exception:
        model_short = "leader"

    app._write("")
    app._write(
        f"[bold #7aa2f7]-- btw  {time.strftime('%H:%M:%S')}"
        f"  {t('btw.header_viewing').format(role=role_name, model=model_short)} --[/bold #7aa2f7]"
    )
    for ln in disp_lines:
        app._write(f"  {ln[:100]}")
    if was_truncated:
        app._write(f"[dim]  {t('btw.lines_hidden').format(n=len(raw_lines)-12)}[/dim]")

    sc = _SPINNER[app._spin % len(_SPINNER)]
    app._set_live(
        f"[dim]{sc}[/dim] [bold]{role_name}[/bold]\n"
        f"[dim]+-- {t('btw.thinking')}[/dim]"
    )

    def _run() -> None:
        try:
            from ...shared.btw_inline import stream_btw_response
            chunks: list[str] = []
            for text in stream_btw_response(
                active=active, tier=tier, role_name=role_name, note=msg
            ):
                chunks.append(text)
                so_far    = "".join(chunks)
                ln_so_far = [l for l in so_far.split("\n") if l.strip()]
                last6     = ln_so_far[-6:]
                spin_c    = _SPINNER[app._spin % len(_SPINNER)]
                live_parts = [
                    f"[dim]{spin_c}[/dim] [bold]{role_name}[/bold]",
                    f"[dim]+-- {t('btw.thinking')}[/dim]",
                ]
                if last6:
                    live_parts.append(f"[dim]    +-- {last6[0][:96]}[/dim]")
                    for l in last6[1:]:
                        live_parts.append(f"[dim]        {l[:96]}[/dim]")
                def _upd(pts=live_parts):
                    app._set_live("\n".join(pts))
                    if app._app: app._app.invalidate()
                app._safe_ui(_upd)

            answer = "".join(chunks).strip()

            def _show():
                app._set_live("")
                if "[STOP_WORKFLOW]" in answer:
                    clean_ans = answer.replace("[STOP_WORKFLOW]", "").strip()
                    if clean_ans:
                        app._write(f"[bold #f7768e]* {t('btw.system')}[/bold #f7768e] [dim]({t('btw.analyzing_cmd')})[/dim]")
                        app._write(f"[#f7768e]    +--[/#f7768e] {clean_ans}")
                    from ....runtime import session as ws
                    app._write("")
                    app._write(f"[bold #f7768e]* {t('btw.workflow')}[/bold #f7768e]  [bold]{t('btw.stop_signal')}[/bold]")
                    app._write(f"[dim]+-- {t('btw.stopping')}[/dim]")
                    try:
                        ws.request_pipeline_stop()
                    except Exception:
                        pass
                    app._write(f"[dim]+--[/dim] {t('del.clear_prompt')}")
                    app._post_delete_clear_mode = True
                elif answer:
                    clean_ans = answer.replace("[STOP_WORKFLOW]", "").strip()
                    words, curr, wchunks = clean_ans.split(), "", []
                    for w in words:
                        if len(curr) + len(w) + 1 > 100:
                            wchunks.append(curr); curr = w
                        else:
                            curr = (curr + " " + w).strip()
                    if curr:
                        wchunks.append(curr)
                    app._write(f"[bold #9ece6a]+-- {role_name}[/bold #9ece6a] [dim]({t('btw.reply_label')})[/dim]")
                    for i, wc in enumerate(wchunks):
                        pfx = "    +--" if i == 0 else "       "
                        app._write(f"[#9ece6a]{pfx}[/#9ece6a] {wc}")
                else:
                    app._write(f"[dim]+-- {t('btw.no_reply').format(role=role_name)}[/dim]")
                if app._app: app._app.invalidate()

            app._safe_ui(_show)

        except Exception as e:
            def _err():
                app._set_live("")
                app._write(f"[red]✗ {t('btw.error')}: {e}[/red]")
                if app._app: app._app.invalidate()
            app._safe_ui(_err)

    threading.Thread(target=_run, daemon=True).start()


__all__ = ["handle_btw_inline"]
