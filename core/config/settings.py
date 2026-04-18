from __future__ import annotations

import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv


def load_environment(console) -> None:
    env_path = find_dotenv(usecwd=True)
    if not env_path:
        config_dir = Path(__file__).parent.parent.parent
        candidate = config_dir / ".env"
        if candidate.exists():
            env_path = str(candidate)
    if env_path:
        load_dotenv(env_path, override=True)
        console.print(f"[dim]✓ Loaded environment from: {env_path}[/dim]")
    else:
        console.print("[yellow]⚠ No .env file found. Using system environment variables.[/yellow]")


def require_openrouter_api_key() -> None:
    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError(
            "OPENROUTER_API_KEY not found. "
            "Copy .env.example → .env and fill in your key.\n"
            "  cp .env.example .env"
        )


def mask_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "")
    if len(key) <= 4:
        return "****"
    return f"***...{key[-4:]}"


def openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "")


def openrouter_base_url() -> str:
    return os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
