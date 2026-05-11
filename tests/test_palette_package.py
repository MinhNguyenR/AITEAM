from __future__ import annotations

from prompt_toolkit.document import Document

from core.cli.python_cli.ui.palette import (
    CommandLexer,
    build_popup_items,
    build_popup_items_all,
    palette_autocomplete_snapshot,
    render_popup_text,
)
from core.cli.python_cli.ui.palette.app import _active_palette_query


def test_palette_autocomplete_snapshot_hides_when_single_exact_monitor_cmd():
    items, visible = palette_autocomplete_snapshot(
        "/ask",
        context="monitor",
        gate_pending=False,
    )
    assert any(c == "/ask" for c, _ in items if c != "__sep__")
    assert visible is False


def test_palette_autocomplete_snapshot_shows_partial_monitor():
    items, visible = palette_autocomplete_snapshot(
        "/a",
        context="monitor",
        gate_pending=False,
    )
    assert visible is True
    flat = [c for c, _ in items if c != "__sep__"]
    assert len(flat) >= 2


def test_palette_at_file_suggestions_use_workspace_root(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    src = workspace / "src"
    src.mkdir()
    (src / "app.py").write_text("print('ok')", encoding="utf-8")
    ignored = workspace / ".git"
    ignored.mkdir()
    (ignored / "hidden.py").write_text("print('hidden')", encoding="utf-8")

    items, visible = palette_autocomplete_snapshot(
        "@src",
        context="monitor",
        gate_pending=False,
        workspace_root=workspace,
    )

    flat = [c for c, _ in items if c != "__sep__"]
    assert visible is True
    assert "@src/app.py" in flat
    assert all("hidden.py" not in c for c in flat)


def test_palette_at_file_suggestions_do_not_leak_repo_root(tmp_path):
    workspace = tmp_path / "other_project"
    workspace.mkdir()
    (workspace / "local.py").write_text("", encoding="utf-8")

    items, _ = palette_autocomplete_snapshot(
        "@core/cli",
        context="monitor",
        gate_pending=False,
        workspace_root=workspace,
    )

    flat = [c for c, _ in items if c != "__sep__"]
    assert flat == []


def test_active_palette_query_prefers_latest_at_or_slash():
    assert _active_palette_query("/explain @src/a") == "@src/a"
    assert _active_palette_query("hello /ask") == "/ask"


def test_build_popup_monitor_shows_sections_for_slash_only():
    items = build_popup_items("/", context="monitor", gate_pending=False)
    assert any(c == "__sep__" for c, _ in items)
    assert any(c == "/ask" for c, _ in items)


def test_build_popup_main_filters_prefix():
    items = build_popup_items("/st", context="main", gate_pending=False)
    cmds = [c for c, _ in items if c != "__sep__"]
    assert "/status" in cmds
    assert all(c.lower().startswith("/st") for c in cmds)


def test_build_popup_main_slash_has_three_sections():
    """Main CLI should produce exactly 3 sections: Tasks, Info & utilities, Global."""
    items = build_popup_items("/", context="main", gate_pending=False)
    seps = [h for c, h in items if c == "__sep__"]
    assert len(seps) == 3, f"expected 3 sections, got: {seps}"
    flat = [c for c, _ in items if c != "__sep__"]
    # Tasks group
    assert "/chat" in flat and "/workflow" in flat
    # Info group
    assert "/status" in flat and "/info" in flat and "/dashboard" in flat
    # Global group
    assert "/back" in flat and "/exit" in flat and "/shutdown" in flat


def test_build_popup_main_sections_order():
    """Section order: Tasks first, Info second, Global last."""
    from core.cli.python_cli.ui.palette.items import _split_registry_into_sections
    sections = _split_registry_into_sections("main")
    keys = [k for k, _ in sections]
    assert keys == ["palette_main_tasks", "palette_main_info", "global"]


def test_ask_chat_context_only_globals():
    """ask_chat context must not contain monitor-specific commands."""
    items, _ = palette_autocomplete_snapshot("/", context="ask_chat", gate_pending=False)
    cmds = [c for c, _ in items if c != "__sep__"]
    for forbidden in ("/btw", "/accept", "/agent", "/ask", "/skip"):
        assert forbidden not in cmds, f"{forbidden} leaked into ask_chat palette"
    for required in ("/back", "/exit", "/shutdown"):
        assert required in cmds, f"{required} missing from ask_chat palette"


def test_palette_autocomplete_snapshot_ask_chat_no_btw():
    items, visible = palette_autocomplete_snapshot("/b", context="ask_chat", gate_pending=False)
    cmds = [c for c, _ in items if c != "__sep__"]
    assert "/btw" not in cmds
    assert "/back" in cmds


def test_build_popup_items_all_matches_slash_only():
    full = build_popup_items_all("main", gate_pending=False)
    slash = build_popup_items("/", "main", gate_pending=False)
    assert full == slash
    n_full = len([c for c, _ in full if c != "__sep__"])
    n_filtered = len([c for c, _ in build_popup_items("/st", "main") if c != "__sep__"])
    assert n_full > n_filtered


def test_render_popup_full_items_with_prefix_query():
    items = build_popup_items_all("main", gate_pending=False)
    rows = render_popup_text("/st", items)
    assert isinstance(rows, list)
    assert len(rows) >= 4
    flat_cmds = [c for c, _ in items if c != "__sep__"]
    assert len(flat_cmds) >= 2


def test_render_popup_returns_formatted_rows():
    items = build_popup_items_all("monitor", gate_pending=False)
    rows = render_popup_text("/ask", items)
    assert isinstance(rows, list)
    assert len(rows) >= 2


def test_command_lexer_prefix_cyan_rest_plain():
    lex = CommandLexer()
    get_line = lex.lex_document(Document("/ask tail"))
    parts = get_line(0)
    text = "".join(p[1] for p in parts)
    assert text == "/ask tail"
    assert parts[0][1] == "/ask"
    assert "bold" in parts[0][0]
    assert parts[1][1] == " tail"
