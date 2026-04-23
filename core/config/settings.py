from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import find_dotenv, load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOWED_BASE_URL_HOSTS = {"openrouter.ai", "api.openrouter.ai"}


def load_environment(console) -> None:
    env_path = find_dotenv(usecwd=True)
    if not env_path:
        candidate = _REPO_ROOT / ".env"
        if candidate.exists():
            env_path = str(candidate)
    if env_path:
        load_dotenv(env_path, override=True)
        console.print("[dim]✓ Loaded environment from: .env[/dim]")
    else:
        console.print("[yellow]⚠ No .env file found. Using system environment variables.[/yellow]")


def prompt_and_persist_key(console) -> str:
    """Interactively prompt user for OPENROUTER_API_KEY and persist to .env."""
    from prompt_toolkit import prompt as _prompt

    console.print("\n[yellow]OPENROUTER_API_KEY not found.[/yellow]")
    console.print("[dim]Get one at https://openrouter.ai/keys[/dim]\n")
    while True:
        key = _prompt("Enter OPENROUTER_API_KEY (sk-or-...): ", is_password=True).strip()
        if key.startswith("sk-or-"):
            break
        console.print("[red]Invalid format — key must start with 'sk-or-'.[/red]")

    env_path = _REPO_ROOT / ".env"
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = [ln for ln in existing.splitlines() if not ln.startswith("OPENROUTER_API_KEY=")]
    lines.append(f"OPENROUTER_API_KEY={key}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    try:
        os.chmod(env_path, 0o600)
    except OSError:
        pass
    os.environ["OPENROUTER_API_KEY"] = key
    console.print("[green]✓ Key saved to .env[/green]\n")
    return key


def require_openrouter_api_key(console=None) -> None:
    """Raise if key missing and no console available; prompt interactively if console given."""
    if not os.getenv("OPENROUTER_API_KEY"):
        if console is not None:
            prompt_and_persist_key(console)
        else:
            raise RuntimeError(
                "OPENROUTER_API_KEY not found. "
                "Run 'aiteam' to set it interactively, or add it to .env."
            )


def mask_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY", "")
    if len(key) <= 4:
        return "****"
    return f"***...{key[-4:]}"


def openrouter_api_key() -> str:
    return os.getenv("OPENROUTER_API_KEY", "")


def openrouter_base_url() -> str:
    url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_BASE_URL_HOSTS:
        raise RuntimeError(
            f"OPENROUTER_BASE_URL '{url}' is not in the allowlist "
            f"({', '.join(sorted(_ALLOWED_BASE_URL_HOSTS))}). "
            "Only https://openrouter.ai/... is accepted."
        )
    return url
