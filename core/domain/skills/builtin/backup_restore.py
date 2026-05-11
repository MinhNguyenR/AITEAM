"""Backup and restore skills backed by SQLite."""

from __future__ import annotations

from core.storage.code_backup import (
    get_file_content_snippet,
    list_backups,
    restore_backup,
    search_backups,
)

from .._categories import SkillCategory
from .._registry import SkillSpec, register


def list_task_backups(task_uuid: str) -> list[dict]:
    return list_backups(task_uuid)


def search_backup(query: str, limit: int = 20) -> list[dict]:
    return search_backups(query, limit=limit)


def preview_backup(backup_id: int, lines: int = 20) -> str:
    return get_file_content_snippet(backup_id, 1, lines)


for spec in (
    SkillSpec("backup.list", "List task backups", "List backup ids and paths for a task.", SkillCategory.BACKUP, tags=("backup",), callable=list_task_backups),
    SkillSpec("backup.search", "Search backups", "Search backup paths and content snippets.", SkillCategory.BACKUP, tags=("backup", "search"), callable=search_backup),
    SkillSpec("backup.preview", "Preview backup", "Preview a small line range from a backup.", SkillCategory.BACKUP, tags=("backup", "preview"), callable=preview_backup),
    SkillSpec("backup.restore", "Restore backup", "Restore a backup id to disk.", SkillCategory.BACKUP, tags=("backup", "restore"), callable=restore_backup),
):
    try:
        register(spec)
    except ValueError:
        pass


__all__ = ["list_task_backups", "preview_backup", "restore_backup", "search_backup"]
