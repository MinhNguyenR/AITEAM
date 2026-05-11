"""Long-running Secretary subprocess.

A single ``python -u -c <bootstrap>`` child process is spawned per
``AgentRuntime``. Worker agents emit ``secretary_command`` events; the
runtime routes them through this class instead of letting each agent
spawn its own ``subprocess.run`` (which was the source of the
``python.exe``/``bash.exe`` accumulation seen on Windows).

Communication protocol (parent -> child via stdin):
    Each request is a single JSON line:
        {"id": str, "argv": [...], "cwd": str, "timeout": float, "env": {...}}
    Two control kinds also exist:
        {"kind": "ping", "id": str}
        {"kind": "shutdown"}

Communication protocol (child -> parent via stdout):
    Each result is wrapped with a record-separator frame so child stdout
    pollution (e.g. progress bars from git/npm) cannot corrupt the JSON
    channel. The frame is::

        \\x1e__AITR_RESULT__\\x1f<json>\\x1e\\n

    Anything outside this frame is treated as untrusted noise and logged
    to ``secretary.log`` rather than parsed.

stderr from the child is captured to ``secretary.log`` (rotating by
size). The child runs each command with ``stdout=PIPE, stderr=PIPE,
stdin=DEVNULL`` so child grandchildren cannot inherit the parent's
stdout — the framing protocol is therefore defence-in-depth, not the
only line of isolation.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import threading
import time
import uuid
from concurrent.futures import Future
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Record-separator framing — picked over \x02/\x03 because RS/US (ASCII 30/31)
# is the canonical ANSI separator and even rarer in real-world output.
_RS = "\x1e"
_US = "\x1f"
_RESULT_TAG = "__AITR_RESULT__"
_FRAME_PREFIX = _RS + _RESULT_TAG + _US

_LOG_ROTATE_BYTES = 5 * 1024 * 1024  # 5 MB

_BOOTSTRAP_SCRIPT = r"""
import json
import os
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

_RS = "\x1e"
_US = "\x1f"
_RESULT_TAG = "__AITR_RESULT__"
_MAX_OUTPUT = 2 * 1024 * 1024  # 2 MB cap per stream

_stdout_lock = threading.Lock()


def _write_result(payload):
    line = _RS + _RESULT_TAG + _US + json.dumps(payload, ensure_ascii=False) + _RS + "\n"
    with _stdout_lock:
        sys.stdout.write(line)
        sys.stdout.flush()


def _kill_tree(proc):
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=5,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            time.sleep(0.5)
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def _run_command(req):
    cmd_id = str(req.get("id") or "")
    argv = req.get("argv") or []
    cwd = req.get("cwd") or "."
    timeout = float(req.get("timeout") or 30.0)
    env_extra = req.get("env")

    if not isinstance(argv, list) or not argv:
        _write_result(
            {"id": cmd_id, "exit_code": 2, "stdout": "", "stderr": "argv required",
             "duration_ms": 0, "timed_out": False}
        )
        return

    full_env = os.environ.copy()
    if isinstance(env_extra, dict):
        full_env.update({str(k): str(v) for k, v in env_extra.items()})

    creationflags = 0
    preexec_fn = None
    start_new_session = False
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        start_new_session = True

    started = time.monotonic()
    cwd_arg = cwd if os.path.isdir(cwd) else None
    proc = None
    try:
        proc = subprocess.Popen(
            [str(part) for part in argv],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=cwd_arg,
            env=full_env,
            creationflags=creationflags,
            start_new_session=start_new_session,
            shell=False,
        )
    except (FileNotFoundError, OSError) as exc:
        _write_result(
            {"id": cmd_id, "exit_code": 127, "stdout": "", "stderr": str(exc),
             "duration_ms": int((time.monotonic() - started) * 1000), "timed_out": False}
        )
        return
    except Exception as exc:
        _write_result(
            {"id": cmd_id, "exit_code": 1, "stdout": "", "stderr": f"secretary error: {exc}",
             "duration_ms": int((time.monotonic() - started) * 1000), "timed_out": False}
        )
        return

    timed_out = False
    try:
        stdout_b, stderr_b = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_tree(proc)
        try:
            stdout_b, stderr_b = proc.communicate(timeout=2.0)
        except Exception:
            stdout_b, stderr_b = b"", b"timeout reached"
        timed_out = True
    exit_code = proc.returncode if proc.returncode is not None else -1

    out_b = stdout_b or b""
    err_b = stderr_b or b""
    out = out_b[:_MAX_OUTPUT].decode("utf-8", errors="replace")
    err = err_b[:_MAX_OUTPUT].decode("utf-8", errors="replace")
    if len(out_b) > _MAX_OUTPUT:
        out += "\n... [truncated]"
    if len(err_b) > _MAX_OUTPUT:
        err += "\n... [truncated]"

    _write_result(
        {
            "id": cmd_id,
            "exit_code": int(exit_code),
            "stdout": out,
            "stderr": err,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "timed_out": timed_out,
        }
    )


def main():
    sys.stderr.write("[secretary] bootstrap ready\n")
    sys.stderr.flush()
    pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="secretary-")
    try:
        for raw in iter(sys.stdin.readline, ""):
            line = raw.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                sys.stderr.write("[secretary] bad json: %s\n" % exc)
                sys.stderr.flush()
                continue
            kind = req.get("kind")
            if kind == "shutdown":
                break
            if kind == "ping":
                _write_result({"id": req.get("id", ""), "kind": "pong", "ts": time.time()})
                continue
            pool.submit(_run_command, req)
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


main()
"""


class SecretaryError(RuntimeError):
    pass


class SecretaryProcess:
    """Wraps the long-running secretary subprocess.

    Commands are submitted via :meth:`submit` and return a ``concurrent.futures.Future``
    that resolves to a result dict with keys ``exit_code``, ``stdout``, ``stderr``,
    ``duration_ms``, ``timed_out``. The subprocess is spawned lazily on first use.
    """

    def __init__(self, *, log_path: Path | None = None) -> None:
        from ..tracing.store import default_trace_root  # local import to avoid cycle

        self.log_path = Path(log_path) if log_path is not None else default_trace_root() / "secretary.log"
        self._stdin_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._proc: subprocess.Popen | None = None
        self._pending: dict[str, Future] = {}
        self._reader: threading.Thread | None = None
        self._stderr_reader: threading.Thread | None = None
        self._closed = False

    # ── Public API ────────────────────────────────────────────────────────

    def submit(
        self,
        argv: list[str],
        *,
        cwd: str = ".",
        timeout: float = 30.0,
        env: dict[str, str] | None = None,
    ) -> Future:
        """Submit a command. Returns a Future of the result dict."""
        if not isinstance(argv, list) or not argv:
            raise SecretaryError("argv must be a non-empty list")
        cmd_id = uuid.uuid4().hex[:12]
        future: Future = Future()
        request = {
            "id": cmd_id,
            "argv": [str(part) for part in argv],
            "cwd": str(cwd or "."),
            "timeout": max(0.5, float(timeout)),
            "env": {str(k): str(v) for k, v in (env or {}).items()},
        }
        proc = self._ensure_proc()
        line = json.dumps(request, ensure_ascii=False) + "\n"
        with self._state_lock:
            self._pending[cmd_id] = future
        try:
            with self._stdin_lock:
                assert proc.stdin is not None
                proc.stdin.write(line.encode("utf-8"))
                proc.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            with self._state_lock:
                self._pending.pop(cmd_id, None)
            future.set_exception(SecretaryError(f"secretary stdin write failed: {exc}"))
            self._respawn_if_dead()
        return future

    def terminate(self, *, timeout: float = 3.0) -> None:
        """Cleanly stop the subprocess. Safe to call multiple times."""
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            proc = self._proc
        if proc is None:
            return
        # Send graceful shutdown request first.
        try:
            with self._stdin_lock:
                if proc.stdin is not None and not proc.stdin.closed:
                    proc.stdin.write(b'{"kind":"shutdown"}\n')
                    proc.stdin.flush()
                    proc.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
        # Fail any still-pending futures so callers don't hang forever.
        with self._state_lock:
            pending = list(self._pending.items())
            self._pending.clear()
        for _cmd_id, fut in pending:
            if not fut.done():
                fut.set_exception(SecretaryError("secretary shutdown before result"))

    def is_alive(self) -> bool:
        with self._state_lock:
            proc = self._proc
        return proc is not None and proc.poll() is None

    # ── Internals ─────────────────────────────────────────────────────────

    def _ensure_proc(self) -> subprocess.Popen:
        with self._state_lock:
            if self._closed:
                raise SecretaryError("secretary already terminated")
            if self._proc is not None and self._proc.poll() is None:
                return self._proc
            self._spawn_locked()
            assert self._proc is not None
            return self._proc

    def _spawn_locked(self) -> None:
        # Caller must hold ``_state_lock``.
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            proc = subprocess.Popen(
                [sys.executable, "-u", "-c", _BOOTSTRAP_SCRIPT],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                shell=False,
            )
        except OSError as exc:
            raise SecretaryError(f"failed to spawn secretary: {exc}") from exc
        self._proc = proc
        self._reader = threading.Thread(
            target=self._stdout_loop,
            args=(proc,),
            name="aitr-secretary-stdout",
            daemon=True,
        )
        self._stderr_reader = threading.Thread(
            target=self._stderr_loop,
            args=(proc,),
            name="aitr-secretary-stderr",
            daemon=True,
        )
        self._reader.start()
        self._stderr_reader.start()

    def _respawn_if_dead(self) -> None:
        with self._state_lock:
            if self._closed:
                return
            if self._proc is None or self._proc.poll() is not None:
                # Drop pending futures — old subprocess is gone, results lost.
                pending = list(self._pending.items())
                self._pending.clear()
                self._proc = None
            else:
                pending = []
        for _cmd_id, fut in pending:
            if not fut.done():
                fut.set_exception(SecretaryError("secretary subprocess died"))

    def _stdout_loop(self, proc: subprocess.Popen) -> None:
        """Parse newline-terminated framed lines from child stdout.

        Each line is either a control frame (``\\x1e__AITR_RESULT__\\x1f...\\x1e``)
        or untrusted noise. Newline (``\\n``) is the only safe separator
        because child grandchildren may emit arbitrary bytes that contain
        record-separator characters.
        """
        assert proc.stdout is not None
        buffer = bytearray()
        try:
            while True:
                chunk = proc.stdout.read1(4096) if hasattr(proc.stdout, "read1") else proc.stdout.read(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                while True:
                    nl = buffer.find(b"\n")
                    if nl < 0:
                        break
                    line_bytes = bytes(buffer[:nl])
                    del buffer[: nl + 1]
                    line = line_bytes.decode("utf-8", errors="replace")
                    if line:
                        self._handle_frame(line)
        except (BrokenPipeError, OSError):
            pass
        finally:
            self._respawn_if_dead()

    def _handle_frame(self, frame: str) -> None:
        """Parse one stdout line; dispatch the JSON result to its Future.

        Lines that don't match the framing protocol are logged as noise and
        silently dropped. The frame body is bracketed by the trailing RS so
        we strip exactly one of those — anything past it is unexpected.
        """
        # Trim trailing whitespace + record-separator. Windows text-mode write
        # converts ``\n`` to ``\r\n`` so the frame may arrive with a stray ``\r``
        # after the closing RS.
        frame = frame.rstrip("\r\n\x1e \t")
        if not frame.startswith(_FRAME_PREFIX):
            self._log_noise(frame + "\n")
            return
        body = frame[len(_FRAME_PREFIX) :]
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            self._log_noise(f"[malformed result frame: {exc}] {body!r}\n")
            return
        cmd_id = str(payload.get("id") or "")
        with self._state_lock:
            fut = self._pending.pop(cmd_id, None)
        if fut is not None and not fut.done():
            fut.set_result(dict(payload))

    def _stderr_loop(self, proc: subprocess.Popen) -> None:
        """Capture child stderr to secretary.log (rotated by size)."""
        assert proc.stderr is not None
        try:
            for raw in iter(proc.stderr.readline, b""):
                self._log_noise(raw.decode("utf-8", errors="replace"))
        except (BrokenPipeError, OSError):
            pass

    def _log_noise(self, text: str) -> None:
        if not text:
            return
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            # Rotate the log when it grows past _LOG_ROTATE_BYTES so it never
            # eats the disk in a long-lived runtime.
            if self.log_path.exists() and self.log_path.stat().st_size > _LOG_ROTATE_BYTES:
                rotated = self.log_path.with_suffix(self.log_path.suffix + ".1")
                try:
                    if rotated.exists():
                        rotated.unlink()
                    self.log_path.rename(rotated)
                except OSError:
                    pass
            with self.log_path.open("a", encoding="utf-8") as fh:
                fh.write(text if text.endswith("\n") else text + "\n")
        except OSError:
            pass


__all__ = ["SecretaryProcess", "SecretaryError"]
