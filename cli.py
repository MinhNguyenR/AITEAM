"""Thin bootstrap entrypoint for core.cli.app."""

from core.cli.app import cli, main_loop

if __name__ == "__main__":
    main_loop()