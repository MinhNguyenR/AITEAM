from __future__ import annotations

import os
from pathlib import Path
import string


def browse_directories(raw_path: str = "") -> dict:
    roots = filesystem_roots()
    if raw_path:
        current = Path(raw_path).expanduser()
    else:
        current = Path.cwd()
    try:
        current = current.resolve()
    except OSError:
        current = Path.cwd().resolve()
    if not current.exists() or not current.is_dir():
        current = Path.cwd().resolve()

    entries: list[dict] = []
    try:
        children = sorted(
            [child for child in current.iterdir() if child.is_dir()],
            key=lambda item: item.name.lower(),
        )
    except OSError:
        children = []
    for child in children[:300]:
        try:
            resolved = child.resolve()
        except OSError:
            continue
        entries.append({"name": child.name, "path": str(resolved)})
    parent = ""
    try:
        if current.parent != current:
            parent = str(current.parent)
    except OSError:
        parent = ""
    return {
        "current": str(current),
        "parent": parent,
        "roots": roots,
        "entries": entries,
    }


def pick_directory(initial: str = "") -> dict:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:
        return {"ok": False, "path": "", "error": f"native picker unavailable: {exc}"}

    root = None
    try:
        initial_path = Path(initial).expanduser() if initial else Path.cwd()
        if not initial_path.exists() or not initial_path.is_dir():
            initial_path = Path.cwd()
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        selected = filedialog.askdirectory(
            parent=root,
            initialdir=str(initial_path.resolve()),
            title="Choose trackaiteam workspace",
            mustexist=True,
        )
        if not selected:
            return {"ok": False, "path": "", "error": "selection cancelled"}
        path = Path(selected).resolve()
        if not path.exists() or not path.is_dir():
            return {"ok": False, "path": "", "error": "selected path is not a directory"}
        return {"ok": True, "path": str(path), "error": ""}
    except Exception as exc:
        return {"ok": False, "path": "", "error": str(exc)}
    finally:
        if root is not None:
            try:
                root.destroy()
            except Exception:
                pass


def filesystem_roots() -> list[dict]:
    if os.name == "nt":
        roots = []
        for letter in string.ascii_uppercase:
            path = f"{letter}:\\"
            if Path(path).exists():
                roots.append({"name": path, "path": path})
        return roots
    return [{"name": "/", "path": "/"}]
