"""The FRAMEGEN_PATCH marker the plugin leaves in a directory it patched through Steam."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .launch_options import is_managed


@dataclass(frozen=True)
class SteamGame:
    """What a patch made through the Steam game list records about the game."""

    appid: str
    name: str
    original_launch_options: str




def build(
    *,
    dll_name: str,
    target_dir: Path,
    backed_up_files: list[str],
    optiscaler_version: str,
    family: str,
    patched_at: str,
    steam_game: SteamGame | None = None,
) -> dict:
    """The marker's details; every patch writes one, a Steam patch also records the game.

    `optiscaler_version` is the library version's id (stable-0.9.4, nightly-20261023).
    """
    return {
        "appid": steam_game.appid if steam_game else "",
        "game_name": steam_game.name if steam_game else "",
        "dll_name": dll_name,
        "target_dir": str(target_dir),
        "original_launch_options": steam_game.original_launch_options if steam_game else "",
        "backed_up_files": backed_up_files,
        "optiscaler_version": optiscaler_version,
        "family": family,
        "patched_at": patched_at,
    }


def describes(details: dict, version_id: str, dll_name: str) -> bool:
    """Whether a marker records a finished patch with this version under this proxy name: patching again
    would place the same."""
    return (
        details.get("complete") is True
        and details.get("optiscaler_version") == version_id
        and details.get("dll_name") == dll_name
    )


def original_launch_options(current: str | None, stored: str | None) -> str | None:
    """The user's own launch options to restore on unpatch.

    Options stored by an earlier patch (None when there was none) win over the current ones,
    which may be ours; options the plugin itself wrote are never treated as the user's. `current`
    is None when Steam didn't say what they are: then only stored options can be kept, and without
    them the user's are unknown (None): a patch would lose them for good, so it mustn't happen.
    """
    if stored and not is_managed(stored):
        return stored
    if current is None:
        return None if stored is None else ""
    return "" if is_managed(current) else current
