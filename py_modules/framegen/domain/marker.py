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
    fsr4_variant: str,
    fsr4_variant_label: str,
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
        "fsr4_variant": fsr4_variant,
        "fsr4_variant_label": fsr4_variant_label,
        "patched_at": patched_at,
    }


def original_launch_options(current: str, stored: str) -> str:
    """The user's own launch options to restore on unpatch.

    Options stored by an earlier patch win over the current ones (which may be
    ours); options the plugin itself wrote are never treated as the user's.
    """
    original = current or ""
    if stored and not is_managed(stored):
        original = stored
    return "" if is_managed(original) else original
