from __future__ import annotations

import os
import sys
from typing import Optional

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.bootstrap import ensure_project_root

ensure_project_root()

import click

from core.cli.pythonCli.app_menu import (
    PROJECT_ROOT,
    _run_start_entry,
    _show_context_entry,
    main_loop as _menu_main_loop,
    run_start,
    run_workflow,
    show_context,
    show_dashboard,
    show_info,
    show_settings,
    show_status,
)
from core.cli.pythonCli.nav import NavToMain
from core.cli.pythonCli.state import get_cli_settings
from core.cli.pythonCli.chrome.ui import PASTEL_BLUE, console


def main_loop():
    try:
        _menu_main_loop()
    except (KeyboardInterrupt, EOFError):
        console.print(f"\n[{PASTEL_BLUE}]Goodbye.[/{PASTEL_BLUE}]")
        raise SystemExit(0)


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    if ctx.invoked_subcommand is None:
        main_loop()


@cli.command()
@click.argument("prompt", required=False)
def start(prompt: Optional[str]):
    try:
        _run_start_entry((prompt or "").strip())
    except NavToMain:
        pass


@cli.command()
def check():
    try:
        _show_context_entry()
    except NavToMain:
        pass


@cli.command()
def status():
    try:
        show_status()
    except NavToMain:
        pass


@cli.command()
def info():
    try:
        show_info()
    except NavToMain:
        pass


@cli.command("change")
def change_cmd():
    try:
        show_info()
    except NavToMain:
        pass


@cli.command("settings")
def settings_cmd():
    try:
        show_settings()
    except NavToMain:
        pass


@cli.command("dashboard")
def dashboard_cmd():
    try:
        show_dashboard(get_cli_settings(), project_root=os.getcwd())
    except NavToMain:
        pass


@cli.command("workflow")
def workflow_cmd():
    run_workflow()


__all__ = [
    "PROJECT_ROOT",
    "cli",
    "main_loop",
    "run_start",
    "show_context",
    "run_workflow",
]
