"""Mixin: _write, _set_live, _get_all_lines, _replay_history."""
from __future__ import annotations

from ._utils import _r2a
from core.cli.python_cli.i18n import t


class _ContentMixin:

    def _write(self, markup: str, indent: bool = False) -> None:
        self._history_raw.append(_r2a(markup))
        try:
            from ....runtime import session as ws
            ws.append_stream_line(markup)
        except Exception:
            pass
        if self._app:
            self._app.invalidate()

    def _set_live(self, markup: str) -> None:
        """Set live step content. Each markup line is converted separately so ANSI codes
        don't bleed across lines when the string is later split by newline.

        Appends \\x1b[K (erase-to-EOL) on every line so old longer lines are cleared.
        When content shrinks, pads with blank lines to overwrite stale content below.
        """
        prev_count = getattr(self, "_prev_live_line_count", 0)
        if not markup:
            # Push blank lines to erase any stale live content
            if prev_count:
                self._live_raw = "\n".join("\x1b[K" for _ in range(prev_count))
            else:
                self._live_raw = ""
            self._prev_live_line_count = 0
            return
        lines = markup.split("\n")
        n = len(lines)
        ansi = [_r2a(line).replace("\r", "") + "\x1b[K" for line in lines]
        # Pad with blank erase-lines if content shrank
        for _ in range(max(0, prev_count - n)):
            ansi.append("\x1b[K")
        self._prev_live_line_count = n
        self._live_raw = "\n".join(ansi)

    def _get_all_lines(self) -> list[str]:
        lines = list(self._history_raw)
        if self._live_raw:
            lines.append(self._live_raw)
        return lines

    def _safe_ui(self, fn) -> None:
        """Thread-safe UI dispatch; silently no-ops if the event loop is gone."""
        try:
            if self._app and self._app.loop:
                self._app.loop.call_soon_threadsafe(fn)
                return
        except Exception:
            pass
        try:
            fn()
        except Exception:
            pass

    def _copy_to_clipboard(self) -> None:
        import re, subprocess, sys
        _ansi = re.compile(r'\x1b\[[0-9;]*[mGKHFJABCDsuhl]')
        lines = list(self._history_raw)
        if self._live_raw:
            lines.append(self._live_raw)
        plain = "\n".join(_ansi.sub("", ln) for ln in lines)
        try:
            if sys.platform == "win32":
                subprocess.run(["clip"], input=plain.encode("utf-16-le"), check=True)
            elif sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=plain.encode("utf-8"), check=True)
            else:
                subprocess.run(["xclip", "-selection", "clipboard"],
                               input=plain.encode("utf-8"), check=True)
            self._write(f"[dim]  OK {t('ui.copy_ok')}[/dim]")
        except Exception as e:
            self._write(f"[dim]  ERR {t('ui.copy_fail').format(e=e)}[/dim]")

    def _replay_history(self) -> None:
        try:
            from ....runtime import session as ws
            for markup in ws.get_stream_history():
                self._history_raw.append(_r2a(markup))
                # Check for localized versions or base markers
                if "Generate state.json" in markup or t("pipeline.gen_state_doing") in markup:
                    self._completed_nodes.add("ambassador")
                    self._ambassador_done_written = True
                if "Generate context.md" in markup or t("pipeline.gen_context") in markup:
                    self._completed_nodes.add("leader_generate")
                if any(x in markup for x in ["Pipeline complete", "Pipeline failed", "Finalize", t("pipeline.complete"), t("pipeline.failed")]):
                    self._completed_nodes.update(
                        {"ambassador", "leader_generate", "human_context_gate", "restore_worker", "finalize_phase1"}
                    )
        except Exception:
            pass


__all__ = ["_ContentMixin"]
