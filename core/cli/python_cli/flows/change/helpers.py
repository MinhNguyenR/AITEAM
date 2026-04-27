from __future__ import annotations

import textwrap

from rich.console import Group
from rich.markup import escape
from rich.text import Text

from core.cli.python_cli.chrome.ui import console
from core.config import config


def indexed_workers() -> list[dict]:
    return list(config.list_workers())


def score_bar(val: float, width: int = 28) -> str:
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "—"
    if v > 1.0 + 1e-9:
        x = max(0.0, min(1.0, v / 100.0)) if v <= 100.0 else 1.0
    else:
        x = max(0.0, min(1.0, v))
    n = int(round(x * width))
    return f"{'#' * n}{'.' * (width - n)} {v:.4g}"


def prompt_panel_content(has_prompt_override: bool, prompt_info: dict) -> Text | Group:
    cw = console.size.width or 100
    wrap_w = max(56, min(cw - 8, 110))
    if has_prompt_override and (prompt_info.get("prompt") or "").strip():
        raw = str(prompt_info["prompt"])
        wrapped = textwrap.fill(raw, width=wrap_w, replace_whitespace=False, drop_whitespace=False)
        main = Text.from_markup(escape(wrapped))
        ts = prompt_info.get("updated_at")
        if ts:
            foot = Text.from_markup(f"[dim]Cập nhật: {escape(str(ts)[:19])}[/dim]")
            return Group(main, Text(""), foot)
        return main
    return Text.from_markup(
        "[bold]System Prompt[/bold] [dim](mặc định)[/dim]\n\n"
        "Đang dùng prompt gốc của framework — [dim]nội dung không hiển thị để bảo vệ cấu hình nội bộ[/dim].\n\n"
        "Gõ [bold]change prompt[/bold] hoặc [bold]prompt[/bold] để nhập prompt tùy chỉnh; "
        "sau khi lưu, toàn bộ nội dung bạn nhập sẽ hiển thị tại đây."
    )


def price_str(pricing: dict) -> str:
    inp = pricing.get("input", 0.0)
    out = pricing.get("output", 0.0)
    if inp == 0 and out == 0:
        return "N/A"
    return f"${inp:.2f}/${out:.2f}"


__all__ = ["indexed_workers", "score_bar", "prompt_panel_content", "price_str"]
