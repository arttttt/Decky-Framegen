"""How a patched game is started: Wine DLL overrides and the Steam launch options."""

from __future__ import annotations

from .bundle import VALID_DLL_NAMES

_ASI_PROXY = "OptiScaler.asi"


def override_entry(dll_name: str) -> str | None:
    """The WINEDLLOVERRIDES entry that loads our proxy natively before Wine's builtin DLL.

    An .asi proxy is loaded by the game's ASI loader and needs none.
    """
    if dll_name == _ASI_PROXY:
        return None
    return f"{dll_name.replace('.dll', '')}=n,b"


def wine_dll_overrides(current: str, dll_name: str) -> str:
    """WINEDLLOVERRIDES with our proxy's entry added; Wine separates entries with ';'."""
    entry = override_entry(dll_name)
    if entry is None:
        return current
    return f"{current};{entry}" if current else entry


def managed(dll_name: str) -> str:
    """The Steam launch options for a game patched with the given proxy DLL."""
    entry = override_entry(dll_name)
    prefix = f"WINEDLLOVERRIDES={entry} " if entry else ""
    return f"{prefix}SteamDeck=0 %command%"


def is_managed(options: str) -> bool:
    """Whether launch options were written by the plugin (or are the fgmod wrapper)."""
    if not options or not options.strip():
        return False
    # Earlier versions also wrote the override quoted: WINEDLLOVERRIDES="dxgi=n,b".
    normalized = " ".join(options.replace('"', "").replace("'", "").split())
    tokens = (f"WINEDLLOVERRIDES={override_entry(dll)}" for dll in VALID_DLL_NAMES if override_entry(dll))
    if any(token in normalized for token in tokens):
        return True
    return "fgmod/fgmod" in normalized
