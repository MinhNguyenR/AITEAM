from __future__ import annotations

from unittest import mock

from core.cli.python_cli import cli_prompt


def test_ask_choice_valid_input(monkeypatch):
    vals = iter(["1"])
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(vals))
    got = cli_prompt.ask_choice("Chọn", ["1", "back", "exit"], default="1")
    assert got == "1"


def test_ask_choice_full_exit_word(monkeypatch):
    vals = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(vals))
    got = cli_prompt.ask_choice("Chọn", ["1", "back", "exit"], default="1")
    assert got == "exit"


def test_ask_choice_full_back_word(monkeypatch):
    vals = iter(["back"])
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(vals))
    got = cli_prompt.ask_choice("Chọn", ["1", "back", "exit"], default="1")
    assert got == "back"


def test_ask_choice_single_key_e_is_invalid_loops(monkeypatch):
    # 'e' is invalid → show error → loop → "1" is accepted
    vals = iter(["e", "1"])
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(vals))
    with mock.patch.object(cli_prompt.console, "print") as p:
        got = cli_prompt.ask_choice("Chọn", ["1", "back", "exit"], default="1")
    assert got == "1"
    invalid_lines = [str(c.args[0]) for c in p.call_args_list if c.args and "Invalid" in str(c.args[0])]
    assert len(invalid_lines) == 1


def test_ask_choice_invalid_loops(monkeypatch):
    # invalid → show error → loop → valid input accepted
    vals = iter(["z", "1"])
    monkeypatch.setattr("builtins.input", lambda *args, **kwargs: next(vals))
    with mock.patch.object(cli_prompt.console, "print") as p:
        got = cli_prompt.ask_choice("Chọn", ["1", "back", "exit"], default="1")
    assert got == "1"
    invalid_lines = [str(c.args[0]) for c in p.call_args_list if c.args and "Invalid" in str(c.args[0])]
    assert len(invalid_lines) == 1


def test_wait_enter_returns_on_any_input(monkeypatch):
    call_count = 0

    def fake_input(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return "something typed"

    monkeypatch.setattr("builtins.input", fake_input)
    cli_prompt.wait_enter("Nhấn Enter")
    assert call_count == 1


def test_wait_enter_returns_on_empty(monkeypatch):
    call_count = 0

    def fake_input(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        return ""

    monkeypatch.setattr("builtins.input", fake_input)
    cli_prompt.wait_enter("Nhấn Enter")
    assert call_count == 1


def test_wait_enter_keypress_does_not_leak_to_next_input(monkeypatch):
    monkeypatch.setattr(cli_prompt, "_read_single_key_blocking", lambda: "f")
    next_input_calls = []

    def capture_input(*args, **kwargs):
        next_input_calls.append(args)
        return "1"

    cli_prompt.wait_enter("x")
    monkeypatch.setattr("builtins.input", capture_input)
    got = cli_prompt.ask_choice("Chọn", ["1", "back", "exit"], default="1")
    assert got == "1"
    assert len(next_input_calls) == 1
