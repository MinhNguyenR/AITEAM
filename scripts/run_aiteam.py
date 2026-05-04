"""Dev entry: `python scripts/run_aiteam.py` (same as console script `aiteam`)."""

from core.cli.python_cli.entrypoints.app import main_loop

if __name__ == "__main__":
    main_loop()
