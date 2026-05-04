"""Shared parsing, paths, and tail I/O for tracker."""

from __future__ import annotations

import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config.constants import AI_TEAM_HOME

logger = logging.getLogger(__name__)


def log_path() -> Path:
    p = AI_TEAM_HOME / "usage_log.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def batches_path() -> Path:
    p = AI_TEAM_HOME / "cli_batches.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_last_n_line_strings(path: Path, n: int, encoding: str = "utf-8") -> List[str]:
    n = max(1, n)
    chunk_size = 65536
    lines_rev: List[bytes] = []
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            if pos == 0:
                return []
            buffer = b""
            while pos > 0 and len(lines_rev) < n:
                step = min(chunk_size, pos)
                pos -= step
                f.seek(pos)
                buffer = f.read(step) + buffer
                while len(lines_rev) < n:
                    idx = buffer.rfind(b"\n")
                    if idx == -1:
                        break
                    line_b = buffer[idx + 1 :]
                    buffer = buffer[:idx]
                    lines_rev.append(line_b)
            if len(lines_rev) < n and buffer:
                lines_rev.append(buffer)
    except OSError as e:
        logger.warning("[Tracker] tail read failed: %s", e)
        return []

    lines_rev = lines_rev[:n]
    out: List[str] = []
    for lb in reversed(lines_rev):
        if not lb.strip():
            continue
        try:
            out.append(lb.decode(encoding).rstrip("\r\n"))
        except UnicodeDecodeError:
            out.append(lb.decode(encoding, errors="replace").rstrip("\r\n"))
    return out


def normalize_iso(ts: Optional[str]) -> str:
    if ts:
        return str(ts)
    return datetime.now().isoformat()


def safe_int(v: Any) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError, OverflowError):
        if v not in (None, "", 0, 0.0):
            logger.warning("[Tracker] safe_int failed for %r", v)
        return 0


def safe_float(v: Any) -> float:
    try:
        return float(v or 0.0)
    except (TypeError, ValueError, OverflowError):
        if v not in (None, "", 0, 0.0):
            logger.warning("[Tracker] safe_float failed for %r", v)
        return 0.0


def parse_day(ts: str) -> Optional[date]:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        try:
            return datetime.strptime(ts[:10], "%Y-%m-%d").date()
        except (ValueError, TypeError):
            return None


def parse_usage_timestamp(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    s = str(ts).strip()
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def token_io_totals(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    pin = sum(safe_int(r.get("prompt_tokens")) for r in rows)
    cout = sum(safe_int(r.get("completion_tokens")) for r in rows)
    return {"prompt_tokens": pin, "completion_tokens": cout, "total_tokens": pin + cout}
