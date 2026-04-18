"""
Test: Ambassador → Leader → context.md flow
============================================
Validates the full pipeline:
1. Ambassador parses input → routing JSON
2. Leader reads state.json (with hardware info)
3. Leader generates context.md
"""

import json
import sys
from pathlib import Path

from aiteam_bootstrap import ensure_project_root

_project_root = str(ensure_project_root())

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

console = Console()


def create_test_state(output_dir: Path) -> Path:
    """Create a sample state.json with hardware info from config."""
    from core.config import config

    state = {
        "task": "Build a FastAPI REST API with user authentication",
        "requirements": [
            "User registration with email + password",
            "JWT token authentication",
            "CRUD endpoints for /users",
            "PostgreSQL database with SQLAlchemy ORM",
        ],
        "constraints": {
            "max_response_time_ms": 200,
            "rate_limit": "100 req/min",
            "python_version": "3.11+",
        },
        "hardware": config.get_system_info()["hardware"],
    }

    state_path = output_dir / "state.json"
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    console.print(f"[dim]✓ Created test state.json → {state_path}[/dim]")
    return state_path


def run_ambassador_demo():
    """Demo: Ambassador parses input and returns routing decision."""
    from agents.ambassador import Ambassador

    console.print("\n[bold cyan]━━━ Step 1: Ambassador Routing ━━━[/bold cyan]")

    ambassador = Ambassador(budget_limit_usd=0.50)
    test_input = "Create a FastAPI endpoint with PostgreSQL and JWT auth"

    result = ambassador.execute(test_input)
    routing = json.loads(result)

    console.print(
        Panel(
            json.dumps(routing, indent=2),
            title=f"[bold green]Ambassador Output — {routing['difficulty']}[/bold green]",
            border_style="green",
        )
    )

    return routing


def run_leader_demo(state_path: Path, leader_type: str = "medium"):
    """Demo: Leader reads state.json and generates context.md."""
    from agents.leader import LeaderHigh, LeaderLow, LeaderMed

    leader_map = {
        "low": LeaderLow,
        "medium": LeaderMed,
        "high": LeaderHigh,
    }

    leader_class = leader_map.get(leader_type, LeaderMed)
    leader = leader_class(budget_limit_usd=1.0)

    console.print(f"\n[bold cyan]━━━ Step 2: {leader.agent_name} Generates Context ━━━[/bold cyan]")
    console.print(f"[dim]Model: {leader.model_name}[/dim]")

    context_path = leader.generate_context(state_path)

    context_content = Path(context_path).read_text(encoding="utf-8")

    console.print(
        Panel(
            Markdown(context_content[:2000] + ("..." if len(context_content) > 2000 else "")),
            title=f"[bold magenta]Generated context.md ({len(context_content)} chars)[/bold magenta]",
            border_style="magenta",
        )
    )

    assert Path(context_path).exists(), "context.md was not created!"
    console.print(f"\n[bold green]✓ context.md generated successfully → {context_path}[/bold green]")

    return context_path


def verify_hardware_in_state(state_path: Path):
    """Verify state.json contains hardware info."""
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)

    hw = state.get("hardware", {})
    console.print("\n[bold cyan]━━━ Step 3: Hardware Info in state.json ━━━[/bold cyan]")
    console.print(f"  GPU: {hw.get('gpu', 'N/A')}")
    console.print(f"  Device: {hw.get('device', 'N/A')}")
    console.print(f"  VRAM: {hw.get('vram_total_gb', 'N/A')} GB")
    console.print(f"  RAM: {hw.get('ram_total_gb', 'N/A')} GB")

    assert "gpu" in hw, "Missing GPU info in state.json!"
    assert "device" in hw, "Missing device info in state.json!"
    console.print("[bold green]✓ Hardware info verified[/bold green]")


if __name__ == "__main__":
    console.print("[bold magenta]AI Agentic Framework v6.2 — Pipeline Test[/bold magenta]\n")

    test_dir = Path(_project_root) / ".test_output"
    test_dir.mkdir(exist_ok=True)

    try:
        run_ambassador_demo()
        state_path = create_test_state(test_dir)
        verify_hardware_in_state(state_path)
        run_leader_demo(state_path, "medium")
        console.print("\n[bold green]✅ All tests passed![/bold green]")

    except (OSError, RuntimeError, ValueError, TypeError) as e:
        console.print(f"\n[bold red]❌ Test failed: {e}[/bold red]")
        import traceback

        console.print(traceback.format_exc())
        sys.exit(1)
