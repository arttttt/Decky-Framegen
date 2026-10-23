"""The Steam launch options the plugin sets for a patched game."""

from __future__ import annotations

from .bundle import VALID_DLL_NAMES

_ASI_PROXY = "OptiScaler.asi"


def _override_token(dll_name: str) -> str:
    """Tells Wine to load our proxy DLL (native) before its builtin one."""
    return f"WINEDLLOVERRIDES={dll_name.replace('.dll', '')}=n,b"


def managed(dll_name: str) -> str:
    """The launch options for a game patched with the given proxy DLL."""
    if dll_name == _ASI_PROXY:
        # An ASI is loaded by the game's ASI loader; Wine needs no override.
        return "SteamDeck=0 %command%"
    return f"{_override_token(dll_name)} SteamDeck=0 %command%"


def is_managed(options: str) -> bool:
    """Whether launch options were written by the plugin (or are the fgmod wrapper)."""
    if not options or not options.strip():
        return False
    normalized = " ".join(options.split())
    if any(_override_token(dll) in normalized for dll in VALID_DLL_NAMES if dll != _ASI_PROXY):
        return True
    return "fgmod/fgmod" in normalized
