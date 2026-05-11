"""Rule-based tier classification helpers for the Ambassador agent."""
from __future__ import annotations

import re
from typing import Optional


def _extract_vram(text: str) -> Optional[str]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(GB|MB)", text, re.IGNORECASE)
    return f"{m.group(1)}{m.group(2)}" if m else None


def _detect_language(text: str) -> str:
    patterns = {
        "cuda": r"\b(cuda|__global__|__device__|threadIdx)\b",
        "python": r"\b(python|def\s+\w+|import\s+\w+)\b",
        "cpp": r"\b(c\+\+|cpp|#include|std::)\b",
        "javascript": r"\b(const\s+\w+=|console\.log)\b",
        "rust": r"\b(fn\s+\w+|let\s+mut)\b",
    }
    for lang, pat in patterns.items():
        if re.search(pat, text, re.IGNORECASE):
            return lang
    return "natural"


def _classify_tier_fallback(text: str) -> str:
    """
    Rule-based fallback classification (3 tiers).
    Used when Ambassador API is unavailable (rate limit, timeout, etc).
    Supports both English and Vietnamese keywords.
    """
    t = text.lower()


    # HARD: CUDA, kernel, hardware-bound
    hard_kw = (
        "cuda", "kernel", "vram", "tensor core", "multi-gpu", "nccl", "nvlink",
        "gpu computing", "parallel computing", "sm_90", "tensor cores",
        "rtx", "low-level", "assembly", "write kernel", "memory bound",
        "gpu memory", "warp", "threadidx", "blockidx", "__global__",
    )
    if any(kw in t for kw in hard_kw):
        return "HARD"


    # HARD: system architecture, complex multi-file design, or hardware-bound work
    hard_design_kw = (
        "architect", "kiến trúc sư", "system architect", "design the system",
        "design system", "design architecture", "technical lead",
        "tech lead", "platform design", "infrastructure design",
        "scalability design", "high-level design", "hld",
        "solution architect", "enterprise architecture",
        "system design", "architecture", "distributed", "microservice",
        "theorem", "proof", "numerical", "statistical",
        "backpropagation", "loss function", "convergence",
        "derive", "prove", "thiết kế hệ thống", "kiến trúc",
        "multi-agent", "orchestrat", "pipeline phức",
    )
    if any(kw in t for kw in hard_design_kw):
        return "HARD"


    # MEDIUM: Feature implementation, AI/ML tasks, CRUD, web
    medium_kw = (
        # English
        "write", "create", "implement", "build", "develop", "code",
        "function", "class", "endpoint", "api", "database", "crud",
        "fastapi", "flask", "django", "rest", "sql", "orm",
        "train", "fine-tune", "finetune", "embedding", "vector",
        "rag", "retrieval", "langchain", "llm", "chatbot", "agent",
        "scrape", "parse", "pipeline", "workflow", "integration",
        "machine learning", "deep learning", "neural", "transformer",
        "attention", "gradient", "matrix", "tensor", "model",
        # Vietnamese
        "tạo", "viết", "xây dựng", "lập trình", "thiết kế",
        "huấn luyện", "nhúng", "truy xuất", "mô hình",
        "học máy", "mạng nơ-ron", "phân loại", "dự đoán",
    )
    if any(kw in t for kw in medium_kw):
        return "MEDIUM"


    # LOW: Q&A, explanation, concept
    qa_kw = (
        "what", "why", "how", "explain", "define", "meaning", "purpose",
        "what is", "what are", "?",
        "vì sao", "là gì", "như thế nào", "tại sao", "giải thích",
        "khái niệm", "định nghĩa",
    )
    if any(kw in t for kw in qa_kw):
        return "LOW"


    # Default: MEDIUM (safer than LOW for ambiguous tasks)
    return "MEDIUM"


def _apply_tier_upgrade_rules(tier: str, is_cuda: bool, complexity: float, is_hardware_bound: bool) -> str:
    """Apply CUDA and complexity upgrade rules to the initial tier."""
    if is_cuda:
        return "HARD"
    if complexity > 0.8:
        return "HARD"
    return tier


def _is_restore_request(text: str) -> bool:
    return bool(re.search(r"\b(restore|revert|undo|rollback)\b|khôi\s*phục|hoàn\s*tác", text, re.IGNORECASE))
