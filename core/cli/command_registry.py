# Central registry for CLI command keys and copy.
# Global commands (documented here; wire in each screen's Prompt.choices as needed):
#   shutdown — thoát hẳn ứng dụng CLI (sys.exit).
#   exit — quay về menu chính.
#   back — thoát màn con, lùi một cấp (ở menu gốc: no-op / thông báo dim).

from __future__ import annotations

# --- Main menu (palette + main_loop) ---
# 0 = shutdown, 1 = start, 2 = check, 3 = status, 4 = info, 5 = dashboard, 6 = settings, 7 = help, 8 = workflow
MAIN_MENU_BY_NUMBER: dict[str, str] = {
    "0": "shutdown",
    "1": "start",
    "2": "check",
    "3": "status",
    "4": "info",
    "5": "dashboard",
    "6": "settings",
    "7": "help",
    "8": "workflow",
}

# Aliases accepted by Prompt.ask (same actions as numbers above)
MAIN_MENU_ALIASES: tuple[str, ...] = tuple(MAIN_MENU_BY_NUMBER.values()) + ("exit",)

# Full choice list for main loop (numbers + names + global back)
MAIN_MENU_VALID_CHOICES: tuple[str, ...] = tuple(MAIN_MENU_BY_NUMBER.keys()) + MAIN_MENU_ALIASES + ("back",)

MAIN_PROMPT_LABEL = "Chọn lệnh"

# Rows for Rich table in palette: (key_display, cmd_name, short_description)
MENU_PALETTE_ROWS: tuple[tuple[str, str, str], ...] = (
    ("[1]", "start", "Chọn mode (ask/agent) rồi nhập task"),
    ("[2]", "check", "Xem và xác nhận context.md"),
    ("[3]", "status", "Trạng thái hệ thống (GPU, RAM, API)"),
    ("[4]", "info", "Registry models + usage; đổi model & prompt"),
    ("[5]", "dashboard", "Wallet, budget, usage today/session; history tóm tắt; s/m"),
    ("[6]", "settings", "Auto-accept, workflow view, help terminal mới"),
    ("[7]", "help", "Hướng dẫn (trong app hoặc terminal mới theo setting)"),
    ("[8]", "workflow", "Monitor LangGraph (Textual)"),
    ("[0]", "shutdown", "Thoát"),
)


def menu_commands() -> list[tuple[str, str, str]]:
    """Descriptions for command palette table."""
    return list(MENU_PALETTE_ROWS)


HELP_SCREEN_MARKDOWN = """
# AI Team Blueprint — Hướng dẫn CLI

## Lệnh global

- **`exit`** — Thoát hẳn ứng dụng (`sys.exit`). Dùng được ở menu chính (số **0** hoặc gõ `exit`) và ở một số màn (ví dụ **check** viewer, **status** sau khi xem).
- **`back`** — Lùi một cấp / đóng màn con. Ở menu gốc: thông báo dim (không có cấp trên).

---

## Menu chính (palette + `Chọn lệnh`)

| Số / tên | Lệnh | Mô tả ngắn |
|----------|------|------------|
| **1** `start` | start | Chọn **ask** / **agent** / **back** / **exit** trước, sau đó nhập task |
| **2** `check` | check | Viewer `context.md` (back, edit, delete, run, regenerate, exit) |
| **3** `status` | status | GPU, API key (mask), đường dẫn; sau đó **back** / **exit** |
| **4** `info` | info | Registry models; số role → chi tiết / **change** (model, prompt) |
| **5** `dashboard` | dashboard | Wallet, usage today, budget, usage session; history tóm tắt; **s** mở history đầy đủ |
| **6** `settings` | settings | Auto-accept, workflow view, help external |
| **7** `help` | help | Markdown này (hoặc cửa sổ terminal mới nếu bật help external) |
| **8** `workflow` | workflow | Monitor Textual / list view tùy cấu hình |
| **0** `exit` | exit | Thoát app |

---

## `start` (mode trước, task sau)

- **`ask`** — Ask: chọn hội thoại trước khi gửi task; code + ask chỉ giải thích (cảnh báo trong CLI).
- **`agent`** — Pipeline agent (Ambassador → graph…). Nếu task giống **câu hỏi** (không phải code), CLI chuyển sang **ask** chat mới, không chạy graph.
- **`back`** — Về menu chính (chọn mode). **`exit`** (chọn mode) — Cũng về menu (huỷ start). Gõ **`exit`** tại prompt nhập task — thoát app.

Mỗi lần đã chọn mode (và có task) = một **đợt** trong **dashboard** (khi có append batch).

---

## `check` (context.md viewer)

- **`back`** — Thoát viewer (nếu đang pause gate: giữ pause, không resume).
- **`edit`** — Mở file trong `EDITOR`.
- **`delete`** — Xóa context + dọn state liên quan.
- **`run`** — Chấp nhận context và tiếp tục / resume workflow nếu đang pause.
- **`regenerate`** — Xóa context, nhập task mới để tạo lại.
- **`exit`** — Thoát app.

Màn **CONTEXT.MD REVIEW** (human gate) dùng phím **A/E/R/B/D** (accept / edit / regenerate / back / delete).

---

## `status`

Tải nhanh: bảng Hardware, API, Status & Paths. Cuối màn: **`back`** | **`exit`**.

---

## `info`

- Bảng tất cả role: sau đó nhập **số** hoặc **`back`** để về.
- Trong **chi tiết role** (`change`): lệnh dạng text — `change to <model_id>`, `change prompt`, `change reset`, `back` / `exit`.

---

## `dashboard`

**Màn chính**

- Wallet, usage hôm nay, **BUDGET** (**`b`** chỉnh), **usage session**.
- **History tóm tắt** (đợt gần nhất); **`s`** — bảng đợt đầy đủ (phân trang, pdf, chi tiết đợt, range…); **`d`** — chi tiết một đợt theo số.

**Submenu `s` (history & công cụ)**

- **0** / **back** về dashboard; **exit** thoát app.
- **1** `range`, **2** `pdf`, **`n`/`p`** trang đợt.

---

## `settings`

- **0** — Về menu chính.
- **1** — Toggle auto-accept `context.md`.
- **2** — Workflow view: chain / list.
- **3** — Help: mở **cửa sổ terminal mới** (cùng shell) chạy help khi chọn menu help (toggle).

---

## `workflow`

Theo entrypoint: Textual monitor hoặc **list view** — gõ lệnh theo màn hình (`exit`, `back`, `rewind`, …). Khi agent chạy từ **start**, tiến độ pipeline cập nhật bằng **Rich Live** trong terminal hiện tại (không mở console mới).

---

## `ask` (Ask mode)

Trong phiên Ask: **`YOU>`** — `ask thinking` / `ask standard`; **`back`** thoát Ask; **`exit`** thoát app. Khi chọn chat: `ask create` / rename / delete; không còn `ask show` / `ask exit`.

---

## Công cụ / dữ liệu

- Log usage local: `~/.ai-team/usage_log.jsonl`.
- Đợt CLI (dashboard / PDF): `~/.ai-team/cli_batches.jsonl`.
""".strip()


__all__ = [
    "MAIN_MENU_BY_NUMBER",
    "MAIN_MENU_ALIASES",
    "MAIN_MENU_VALID_CHOICES",
    "MAIN_PROMPT_LABEL",
    "menu_commands",
    "HELP_SCREEN_MARKDOWN",
]
