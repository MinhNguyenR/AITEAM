"""Singleton SqliteSaver for LangGraph checkpoints."""

from __future__ import annotations

import sqlite3
from functools import lru_cache

from langgraph.checkpoint.sqlite import SqliteSaver

from .session import checkpoint_db_path


@lru_cache(maxsize=1)
def get_checkpointer() -> SqliteSaver:
    path = checkpoint_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    saver = SqliteSaver(conn)
    saver.setup()
    return saver
