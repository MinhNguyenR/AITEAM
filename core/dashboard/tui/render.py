from __future__ import annotations

from datetime import datetime
from typing import Optional

from rich.box import DOUBLE, ROUNDED
from rich.panel import Panel
from rich.prompt import Prompt
from rich.style import Style
from rich.table import Table
from rich.text import Text

from core.cli.python_cli.shell.prompt import ask_choice
from core.cli.python_cli.shell.nav import NavToMain
from core.config import config
from core.cli.python_cli.i18n import t
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


def header(title: str, *, out=None) -> None:
    sink = out or console
    sink.print(
        Panel(
            Text(title, style=Style(color=BRIGHT_BLUE, bold=True), justify="center"),
            box=DOUBLE,
            border_style=PASTEL_BLUE,
            padding=(1, 4),
        )
    )
    sink.print()


def fmt_budget_line(name: str, metric: tracker.BudgetMetric) -> str:
    limit_s = "Unlimited" if metric.unlimited else f"${metric.limit_usd:.2f}"
    if metric.unlimited:
        return f"{name}: ${metric.spent_usd:.2f} / {limit_s}"
    return f"{name}: ${metric.spent_usd:.2f} / {limit_s} -> {metric.status}"


def fmt_budget_value(value: Optional[float]) -> str:
    return t('unit.unlimited') if value is None else f"${float(value):.2f}"


def ask_budget_value(label: str, current: Optional[float]) -> Optional[float]:
    from core.cli.python_cli.ui.palette_app import ask_with_palette
    prompt = t("dash.budget_prompt").format(label=label, curr=fmt_budget_value(current))
    try:
        raw = ask_with_palette(f"{prompt} ", context="dashboard_budget", default="").strip()
    except Exception:
        raw = Prompt.ask(f"{prompt} ", default="").strip()
    if raw == "":
        return None
    try:
        val = float(raw)
        if val < 0:
            raise ValueError
        return val
    except ValueError:
        console.print(f"[yellow]{t('nav.invalid_choice')}[/yellow]")
        return current


def pick_range_rows() -> tuple[str, list[dict], Optional[datetime], Optional[datetime]]:
    from core.cli.python_cli.ui.palette_app import ask_with_palette
    while True:
        now = datetime.now()
        console.print(
            Panel(
                f"[bold]1[/bold] {t('dash.range_24h')}\n"
                f"[bold]2[/bold] {t('dash.range_7d')}\n"
                f"[bold]3[/bold] {t('dash.range_30d')}\n"
                f"[bold]4[/bold] {t('dash.range_custom')}\n"
                f"[bold]0[/bold] / [bold]back[/bold] {t('nav.back')}",
                title=f"[bold]{t('dash.range_title')}[/bold]",
                border_style=PASTEL_LAVENDER,
                box=ROUNDED,
            )
        )
        c = ask_choice(t("dash.range_title"), ["1", "2", "3", "4", "0", "back", "exit"], default="1")
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
            try:
                a = ask_with_palette(f"{t('dash.range_from')} ", context="dashboard_history")
                b = ask_with_palette(f"{t('dash.range_to')} ", context="dashboard_history")
            except Exception:
                a = Prompt.ask(f"{t('dash.range_from')} ")
                b = Prompt.ask(f"{t('dash.range_to')} ")
            try:
                since = datetime.fromisoformat(a.strip().replace("Z", "+00:00"))
                until = datetime.fromisoformat(b.strip().replace("Z", "+00:00"))
                if since >= until:
                    console.print(f"[yellow]{t('dash.range_invalid_order')}[/yellow]")
                    continue
            except ValueError:
                console.print(f"[red]{t('dash.range_invalid_fmt')}[/red]")
                continue
        label = f"{since.isoformat(timespec='minutes')} ... {until.isoformat(timespec='minutes')}"
        rows = tracker.read_usage_rows_timerange(since, until)
        return (label, rows, since, until)


def render_history_table(rows: list[dict], title: str) -> None:
    table = Table(box=ROUNDED, width=100, show_lines=False)
    table.add_column(t("dash.time"), style="dim", width=18)
    table.add_column(t("info.role_name"), style="cyan")
    table.add_column(t("dash.model_col"), style="white", overflow="fold")
    table.add_column(t("dash.in_col"), justify="right")
    table.add_column(t("dash.out_col"), justify="right")
    table.add_column(t("dash.tot_col"), justify="right", style="magenta")
    table.add_column(t("dash.cost_col"), justify="right", style="yellow")
    for r in rows:
        table.add_row(
            format_row_time(r),
            str(r.get("role_key") or r.get("agent") or "-"),
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
        u_table.add_row(f"{t('dash.requests')} (session)", str(usage.get("total_requests", 0)))
        u_table.add_row(f"{t('dash.tokens')} (session)", f"{usage.get('total_tokens', 0):,}")
        u_table.add_row(f"{t('dash.spend')} (session)", f"${usage.get('total_cost', 0.0):.4f}")
        console.print(Panel(u_table, title=f"[bold {PASTEL_CYAN}]{t('dash.usage_session')}[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
        by_role = usage.get("by_role") or {}
        if not by_role:
            return
        id_to = {str(w.get("id", "")): w for w in workers}
        r_table = Table(box=ROUNDED, show_header=True, header_style=Style(color=PASTEL_CYAN, bold=True), border_style=PASTEL_BLUE, padding=(0, 1))
        r_table.add_column(t('info.role_key'), style=Style(color=PASTEL_CYAN), width=16)
        r_table.add_column(t('info.role_name'), style=SOFT_WHITE, width=22)
        r_table.add_column(t('dash.model_col'), style="white", width=28)
        r_table.add_column(t('dash.req_col'), justify="right", width=5)
        r_table.add_column(t('dash.tokens'), justify="right", width=10)
        r_table.add_column(t('dash.spend'), justify="right", width=10)
        for rk, stats in sorted(by_role.items(), key=lambda x: x[0]):
            wk = id_to.get(rk, {})
            role_label = str(wk.get("role", "-"))[:22]
            by_model = stats.get("by_model") or {}
            if not by_model:
                r_table.add_row(rk, role_label, str(wk.get("model", "-"))[:28], str(stats.get("requests", 0)), f"{int(stats.get('tokens', 0)):,}", f"${float(stats.get('cost_usd', 0.0)):.4f}")
            else:
                for mid, ms in sorted(by_model.items(), key=lambda x: str(x[0])):
                    r_table.add_row(rk, role_label, (mid or str(wk.get("model", "-")))[:28], str(ms.get("requests", 0)), f"{int(ms.get('tokens', 0)):,}", f"${float(ms.get('cost_usd', 0.0)):.4f}")
        console.print(Panel(r_table, title=f"[bold {PASTEL_CYAN}]{t('dash.usage_role_model_session')}[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
    except (ImportError, RuntimeError, ValueError):
        console.print(f"[dim]{t('dash.usage_render_err')}[/dim]")


def render_wallet_usage(summary: tracker.DashboardSummary, *, out=None) -> None:
    sink = out or console
    wallet_table = Table(box=ROUNDED, show_header=False, border_style=PASTEL_BLUE, padding=(0, 2))
    wallet_table.add_column(t("dash.field_col"), style=Style(color=PASTEL_CYAN), width=22)
    wallet_table.add_column(t("ui.value"), style="white", width=24)
    wallet_table.add_row(t('dash.total_credits'), f"${summary.total_credits:.4f}")
    wallet_table.add_row(t('dash.remaining'), f"${summary.remaining_credits:.4f}")
    sink.print(Panel(wallet_table, title=f"[bold {PASTEL_CYAN}]{t('dash.wallet_live')}[/bold {PASTEL_CYAN}]", border_style=PASTEL_BLUE, box=ROUNDED))
