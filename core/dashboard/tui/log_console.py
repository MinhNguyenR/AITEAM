"""Shared Rich console for dashboard export modules (avoids import cycles)."""
from __future__ import annotations

from rich.console import Console

console = Console()
