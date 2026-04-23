"""Model/prompt override CLI: list, detail, run loop."""

from __future__ import annotations

from core.cli.flows.change.detail_flow import show_role_detail
from core.cli.flows.change.list_flow import pick_role_key_from_indexed_workers, show_change_list


def run_change_flow() -> None:
    while True:
        role_key = show_change_list()
        if role_key is None:
            return
        show_role_detail(role_key)


__all__ = [
    "run_change_flow",
    "show_change_list",
    "show_role_detail",
    "pick_role_key_from_indexed_workers",
]
