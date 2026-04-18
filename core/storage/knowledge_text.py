"""Keyword extraction and FTS/LIKE helpers for knowledge index."""

from __future__ import annotations

import re
import sqlite3
from typing import List, Optional

STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "will", "would", "could", "should", "may", "might", "shall", "can", "need", "dare", "ought", "used",
    "to", "of", "in", "for", "on", "with", "at", "by", "from", "as", "into", "through", "during", "before",
    "after", "above", "below", "between", "out", "off", "over", "under", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "both", "each", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "just", "because",
    "but", "and", "or", "if", "while", "about", "against", "this", "that", "these", "those", "it", "its", "i",
    "me", "my", "we", "our", "you", "your", "he", "him", "his", "she", "her", "they", "them", "their", "what",
    "which", "who", "whom", "any", "also", "up", "down",
    "là", "và", "của", "cho", "trong", "với", "không", "có", "được", "những", "các", "một", "này", "đó", "đây",
    "từ", "để", "khi", "như", "vào", "ra", "lên", "xuống", "đã", "đang", "sẽ", "phải", "rất", "vì", "do", "bởi",
    "nếu", "thì", "mà", "nhưng", "hoặc", "tại", "về", "theo", "sau", "trước", "trên", "dưới", "giữa", "người",
    "ta", "nó", "họ", "chúng", "tôi", "bạn", "anh", "chị", "ông", "bà", "cô", "chú", "bác", "em", "con", "cái",
    "còn", "gì", "ai", "đâu", "nào", "sao", "bao", "nhiêu", "thế", "vậy",
}


def extract_keywords(text: str, top_k: int = 5) -> List[str]:
    if not text or len(text.strip()) < 10:
        return []
    tokens = re.findall(r"\b[a-zA-ZÀ-ỹ]{3,}\b", text.lower())
    if not tokens:
        return []
    freq: dict[str, int] = {}
    total_filtered = 0
    for token in tokens:
        if token not in STOP_WORDS:
            freq[token] = freq.get(token, 0) + 1
            total_filtered += 1
    if not freq:
        return []
    unique_tokens = len(freq)
    ratio = total_filtered / max(unique_tokens, 1)
    scored = [(word, count * (1 + 0.5 * ratio)) for word, count in freq.items()]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [word for word, _ in scored[:top_k]]


def fts_token_terms(keywords: List[str], query_text: str) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for kw in keywords:
        t = kw.strip().lower()
        if len(t) >= 2 and t not in seen:
            seen.add(t)
            out.append(t)
    if not out and query_text.strip():
        for m in re.findall(r"[\wÀ-ỹ]{2,}", query_text.lower()):
            if m not in seen:
                seen.add(m)
                out.append(m)
            if len(out) >= 8:
                break
    return out


def fts_match_expression(terms: List[str]) -> Optional[str]:
    parts: List[str] = []
    for t in terms:
        if any(ch in t for ch in "\x00\n\r"):
            continue
        parts.append('"' + t.replace('"', '""') + '"')
    if not parts:
        return None
    return "{title tags} : (" + " OR ".join(parts) + ")"


def escape_like(s: str) -> str:
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def like_fallback_rows(cursor: sqlite3.Cursor, terms: List[str], limit: int) -> List[tuple]:
    if not terms:
        return []
    kw = max(terms, key=len)
    pat = f"%{escape_like(kw)}%"
    cursor.execute(
        """
        SELECT id, title, tags, path FROM knowledge_index
        WHERE title LIKE ? ESCAPE '\\' OR tags LIKE ? ESCAPE '\\'
        ORDER BY updated_at DESC
        LIMIT ?
        """,
        (pat, pat, limit),
    )
    return cursor.fetchall()
