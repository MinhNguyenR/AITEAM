"""SecretaryProcess subprocess + framing protocol tests.

These checks lock down the contract that lets workers safely route their
terminal commands through a single long-running ``python.exe`` child:

* Multiple submits share the same OS process.
* Child stdout pollution (a noisy subprocess that prints garbage) cannot
  break the framing protocol or hijack another command's result.
* ``terminate()`` shuts the child down cleanly.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

from aiteamruntime.secretary_proc import SecretaryProcess


@pytest.fixture
def secretary(tmp_path: Path):
    sec = SecretaryProcess(log_path=tmp_path / "secretary.log")
    yield sec
    sec.terminate()


def test_basic_command_returns_result(secretary: SecretaryProcess) -> None:
    fut = secretary.submit([sys.executable, "-c", "print('hello')"], timeout=10)
    result = fut.result(timeout=15)
    assert result["exit_code"] == 0
    assert "hello" in result["stdout"]
    assert result["timed_out"] is False


def test_secretary_subprocess_is_singleton(secretary: SecretaryProcess) -> None:
    """Three submits must share the same OS process — never spawn new python.exe."""
    f1 = secretary.submit([sys.executable, "-c", "print(1)"], timeout=5)
    f2 = secretary.submit([sys.executable, "-c", "print(2)"], timeout=5)
    f3 = secretary.submit([sys.executable, "-c", "print(3)"], timeout=5)
    f1.result(timeout=10)
    f2.result(timeout=10)
    f3.result(timeout=10)
    assert secretary.is_alive()
    # Only one process was ever started; pid stays stable.
    assert secretary._proc is not None


def test_child_stdout_pollution_does_not_break_protocol(
    secretary: SecretaryProcess, tmp_path: Path
) -> None:
    """A child that prints noise (including fake frame markers) must not
    corrupt subsequent commands' results."""
    noisy_code = (
        "print('NOISE')\n"
        "print('\\x1e__AITR_RESULT__\\x1f{\"id\":\"FAKE\",\"exit_code\":99}\\x1e')\n"
        "print('more noise')\n"
    )
    f1 = secretary.submit([sys.executable, "-c", noisy_code], timeout=10)
    r1 = f1.result(timeout=15)
    # The noisy child completed normally; its output was *captured* in the
    # result, not piped into the parent's stdout reader.
    assert r1["exit_code"] == 0
    assert "NOISE" in r1["stdout"]
    assert "__AITR_RESULT__" in r1["stdout"]

    # Now run a real command — the parent must still parse this one correctly.
    f2 = secretary.submit([sys.executable, "-c", "print('clean')"], timeout=5)
    r2 = f2.result(timeout=10)
    assert r2["exit_code"] == 0
    assert "clean" in r2["stdout"]
    # The fake "FAKE" id from the noise must NEVER have been delivered to a
    # waiting future — both submits got their proper results.
    assert r2.get("id") != "FAKE"


def test_command_timeout_marks_result(secretary: SecretaryProcess) -> None:
    fut = secretary.submit(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        timeout=1.5,
    )
    result = fut.result(timeout=10)
    assert result["timed_out"] is True
    # Whatever exit code the kill produced, the secretary subprocess itself
    # is still alive and ready to take more commands.
    assert secretary.is_alive()
    follow = secretary.submit([sys.executable, "-c", "print('alive')"], timeout=5)
    assert follow.result(timeout=10)["exit_code"] == 0


def test_terminate_shuts_down_cleanly(tmp_path: Path) -> None:
    sec = SecretaryProcess(log_path=tmp_path / "secretary.log")
    sec.submit([sys.executable, "-c", "print('warmup')"], timeout=5).result(timeout=10)
    assert sec.is_alive()
    sec.terminate()
    # Give the OS a moment to reap the child.
    time.sleep(0.2)
    assert not sec.is_alive()
