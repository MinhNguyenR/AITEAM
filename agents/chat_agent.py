"""Chat agent — inline assistant for workflow TUI and ask mode.

Uses CHAT_MODEL_STANDARD (google/gemini-2.5-flash-lite) from registry.
System prompt covers: workflow pipeline, all roles, all CLI commands.
"""
from __future__ import annotations

from typing import Optional

from core.config import config as _config
from core.config.settings import openrouter_base_url


CHAT_WORKFLOW_SYSTEM_PROMPT = """\
Bạn là Assistant tích hợp trong aiteam — AI agent pipeline để xây dựng phần mềm.

## Workflow Pipeline
Ambassador → Leader/Expert → Human Context Gate → Finalize
- Ambassador: phân tích task, xác định Tier (LOW/MEDIUM/HIGH/EXPERT)
- Leader (LOW/MEDIUM/HIGH): tạo context.md — hướng dẫn chi tiết cho Workers
- Expert: tạo context.md cho task kiến trúc phức tạp (HARD/EXPERT)
- Human Context Gate: user review context.md trước khi Workers thực thi
- Finalize: Workers nhận context.md và viết code thực tế

## Tier
LOW → MEDIUM → HIGH → EXPERT (độ phức tạp và model mạnh hơn theo chiều tăng)

## Roles (từ Model Registry)
- Ambassador — Input Parser & Task Router
- Leader LOW / MEDIUM / HIGH — tạo context.md theo Tier
- Expert — Architecture Expert (task HARD/EXPERT)
- Researcher — Research Specialist (web/docs research)
- Reviewer, Fast Reviewer, Final Reviewer — review code quality
- Worker A–F — viết code theo context.md
- Fix Worker A/B, Advanced Fix Worker A/B — debug, fix bugs
- Compact Worker — xử lý query nhỏ, inline task
- Browser — web search agent
- Secretary — terminal executor
- Commander — Supreme Commander (high-level orchestration)
- Tool Curator — quản lý tool và dependency

## CLI Commands — Workflow TUI (monitor/list view)
  /agent <task>    Bắt đầu agent pipeline với task mới
  /ask <câu hỏi>   Hỏi AI assistant inline (không mở pipeline)
  btw <ghi chú>    Gửi ghi chú cho agent đang chạy (chỉ khi pipeline active)
  check            Xem nội dung context.md đã generate
  accept           Chấp nhận context.md → pipeline tiếp tục
  delete           Từ chối context.md → có thể regenerate (y) hoặc bỏ (n)
  log              Xem activity log gần nhất
  info             Xem thông tin pipeline (tier, model, token count)
  exit / quit / q  Thoát workflow TUI
  task <text>      Bắt đầu task mới (shorthand)

## CLI Commands — Ask Mode (outside TUI)
  ask thinking     Chuyển sang thinking mode (gemini-2.5-flash-lite:exacto)
  ask standard     Quay về standard mode (gemini-2.5-flash-lite)
  back             Quay về menu chính
  exit             Thoát hoàn toàn

## Nguyên tắc trả lời
- Trả lời câu hỏi, giải thích khái niệm, hỗ trợ code/debug
- Khi user muốn tạo/sửa file trong repo: khuyên dùng /agent <task>
- Ngắn gọn, đúng trọng tâm
- Ưu tiên tiếng Việt nếu user dùng tiếng Việt
- Không tuyên bố đã sửa file hay chạy lệnh (chỉ giải thích/gợi ý)
"""


class ChatAgent:
    """Inline chat assistant — reads CHAT_MODEL_STANDARD from registry."""

    def __init__(self, mode: str = "standard") -> None:
        worker_id = "CHAT_MODEL_THINKING" if mode == "thinking" else "CHAT_MODEL_STANDARD"
        cfg = _config.get_worker(worker_id) or {}
        self.model       = str(cfg.get("model") or _config.ASK_CHAT_STANDARD_MODEL)
        self.max_tokens  = int(cfg.get("max_tokens") or 3000)
        self.temperature = float(cfg.get("temperature") if cfg.get("temperature") is not None else 1.2)
        self.top_p       = float(cfg.get("top_p")       if cfg.get("top_p")       is not None else 0.95)

    def ask(
        self,
        question: str,
        history: Optional[list] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Call the model. history = list of {role, content} dicts (no system entry)."""
        from openai import OpenAI

        sys_content = system_prompt or CHAT_WORKFLOW_SYSTEM_PROMPT
        messages: list[dict] = [{"role": "system", "content": sys_content}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": question})

        client = OpenAI(api_key=_config.api_key, base_url=openrouter_base_url())
        resp = client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            top_p=self.top_p,
        )
        return (resp.choices[0].message.content or "").strip()
