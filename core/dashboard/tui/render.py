from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.box import DOUBLE, ROUNDED
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.cli.cli_prompt import ask_choice
from core.cli.nav import NavToMain
from core.config import config
from utils import tracker

from .log_console import console
from .utils import (
    format_row_time,
    safe_float,
    safe_int,
)

PASTEL_BLUE = "#6495ED"
PASTEL_CYAN = "#7FFFD4"
PASTEL_LAVENDER = "#C8C8FF"
BRIGHT_BLUE = "#4169E1"
SOFT_WHITE = "#E8E8F0"


def header(title: str) -> None:
    console.print(
        Panel(
            Text(title, style=Style(color=BRIGHT_BLUE, bold=True), justify="center"),
            box=DOUBLE,
            border_style=PASTEL_BLUE,
            padding=(1, 4),
        )
    )
    console.print()


def fmt_budget_line(name: str, metric: tracker.BudgetMetric) -> str:
    if metric.unlimited:
        return f"{name}: ${metric.spent_usd:.2f} / Unlimited"
    return f"{name}: ${metric.spent_usd:.2f} / ${metric.limit_usd:.2f} -> {metric.status}"


def fmt_budget_value(value: Optional[float]) -> str:
    return "Unlimited" if value is None else f"${float(value):.2f}"


def ask_budget_value(label: str, current: Optional[float]) -> Optional[float]:
    raw = Prompt.ask(f"{label} hiện tại {fmt_budget_value(current)}. Nhập USD mới hoặc để trống = Unlimited", default="").strip()
    if raw == "":
        return None
    try:
        val = float(raw)
        if val < 0:
            raise ValueError
        return val
    except ValueError:
        console.print("[yellow]Giá trị không hợp lệ, giữ nguyên.[/yellow]")
        return current


def pick_range_rows() -> tuple[str, list[dict], Optional[datetime], Optional[datetime]]:
    while True:
        now = datetime.now()
        console.print(
            Panel(
                "[bold]1[/bold] 24 giờ gần nhất\n"
                "[bold]2[/bold] 7 ngày gần nhất\n"
                "[bold]3[/bold] 30 ngày gần nhất\n"
                "[bold]4[/bold] custom ISO (YYYY-MM-DDTHH:MM)\n"
                "[bold]0[/bold] / [bold]back[/bold] về màn trước",
                title="[bold]Chọn khoảng thời gian[/bold]",
                border_style=PASTEL_LAVENDER,
                box=ROUNDED,
            )
        )
        c = ask_choice("Khoảng thời gian", ["1", "2", "3", "4", "0", "back", "exit"], default="1")
        if c == "exit":
            raise NavToMain
        if c in ("0", "back"):
            return ("cancelled", [], None, None)
        if c == "1":
            since, until = now - __import__("datetime").timedelta(hours=24), now
        elif c == "2":
            since, until = now - __import__("datetime").timedelta(days=7), now
        elif c == "3":
            since, until = now - __import__("datetime").timedelta(days=30), now
        else:
            a = Prompt.ask("Từ (ISO)")
            b = Prompt.ask("Đến (ISO)")
            try:
                since = datetime.fromisoformat(a.strip().replace("Z", "+00:00"))
                until = datetime.fromisoformat(b.strip().replace("Z", "+00:00"))
                if since >= until:
                    console.print("[yellow]Khoảng thời gian không hợp lệ: from phải nhỏ hơn to.[/yellow]")
                    continue
            except ValueError:
                console.print("[red]Sai định dạng thời gian, ví dụ: 2026-04-12T16:58[/red]")
                continue
        label = f"{since.isoformat(timespec='minutes')} … {until.isoformat(timespec='minutes')}"
        rows = tracker.read_usage_rows_timerange(since, until)
        return (label, rows, since, until)


def render_history_table(rows: list[dict], title: str) -> None:
    table = Table(box=ROUNDED, width=100, show_lines=False)
    table.add_column("Time", style="dim", width=18)
    table.add_column("Role", style="cyan")
    table.add_column("Model", style="white", overflow="fold")
    table.add_column("In", justify="right")
    table.add_column("Out", justify="right")
    table.add_column("Tot", justify="right", style="magenta")
    table.add_column("USD", justify="right", style="yellow")
    for r in rows:
        table.add_row(
            format_row_time(r),
            str(r.get("role_key") or r.get("agent") or "—"),
            str(r.get("model") or "")[:48],
            f"{safe_int(r.get('prompt_tokens')):,}",
            f"{safe_int(r.get('completion_tokens')):,}",
            f"{safe_int(r.get('total_tokens')):,}",
            f"{safe_float(r.get('cost_usd')):.5f}",
        )
    console.print(Panel(table, title=f"[bold]{title}[/bold]", border_style=PASTEL_CYAN, box=ROUNDED))




def render_session_usage_panel() -> None:
    try:
        from utils.tracker import get_usage_summary

        workers = config.list_workers()
        usage = get_usage_summary(period="session")
        u_table = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
        u_table.add_column("K", style=Style(color=PASTEL_CYAN), width=22)
        u_table.add_column("V", style="white", width=30)
        u_table.add_row("Requests (session)", str(usage.get("total_requests", 0)))
        u_table.add_row("Tokens (session)", f"{usage.get('total_tokens', 0):,}")
        u_table.add_row("Cost (session)", f"${usage.get('total_cost', 0.0):.4f}")
        console.print(Panel(u_table, title=f"[bold {PASTEL_CYAN}]Usage session[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
        by_role = usage.get("by_role") or {}
        if not by_role:
            return
        id_to = {str(w.get("id", "")): w for w in workers}
        r_table = Table(box=ROUNDED, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True), border_style=PASTEL_BLUE, padding=(0, 1))
        r_table.add_column("Role key", style=Style(color=PASTEL_CYAN), width=16)
        r_table.add_column("Role", style=SOFT_WHITE, width=22)
        r_table.add_column("Model", style="white", width=28)
        r_table.add_column("Req", justify="right", width=5)
        r_table.add_column("Tokens", justify="right", width=10)
        r_table.add_column("Cost", justify="right", width=10)
        for rk, stats in sorted(by_role.items(), key=lambda x: x[0]):
            wk = id_to.get(rk, {})
            role_label = str(wk.get("role", "—"))[:22]
            by_model = stats.get("by_model") or {}
            if not by_model:
                r_table.add_row(rk, role_label, str(wk.get("model", "—"))[:28], str(stats.get("requests", 0)), f"{int(stats.get('tokens', 0)):,}", f"${float(stats.get('cost_usd', 0.0)):.4f}")
            else:
                for mid, ms in sorted(by_model.items(), key=lambda x: str(x[0])):
                    r_table.add_row(rk, role_label, (mid or str(wk.get("model", "—")))[:28], str(ms.get("requests", 0)), f"{int(ms.get('tokens', 0)):,}", f"${float(ms.get('cost_usd', 0.0)):.4f}")
        console.print(Panel(r_table, title=f"[bold {PASTEL_CYAN}]Usage theo role / model (session)[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
    except (ImportError, RuntimeError, ValueError):
        console.print("[dim]Không thể render usage session.[/dim]")


def render_wallet_usage(summary: tracker.DashboardSummary):
    wallet_table = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    wallet_table.add_column("Field", style=Style(color=PASTEL_CYAN), width=22)
    wallet_table.add_column("Value", style="white", width=24)
    wallet_table.add_row("Total Credits", f"${summary.total_credits:.4f}")
    wallet_table.add_row("Remaining", f"${summary.remaining_credits:.4f}")
    console.print(Panel(wallet_table, title=f"[bold {PASTEL_CYAN}]WALLET (LIVE)[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
