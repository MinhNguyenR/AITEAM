"""CLI navigation: exit → main menu; back → one level up."""


class NavToMain(Exception):
    """Raise from nested flows to return to the main menu (main_loop)."""


class NavBack(Exception):
    """Raise to return exactly one level up from the current sub-flow."""


def is_nav_exit(line: str) -> bool:
    return (line or "").strip().lower() == "exit"


def is_nav_back(line: str) -> bool:
    return (line or "").strip().lower() == "back"


def raise_if_global_nav(line: str) -> None:
    t = (line or "").strip().lower()
    if t == "exit":
        raise NavToMain
    if t == "back":
        raise NavBack


__all__ = ["NavToMain", "NavBack", "is_nav_exit", "is_nav_back", "raise_if_global_nav"]
