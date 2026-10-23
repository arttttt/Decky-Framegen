"""The FRAMEGEN_PATCH marker the plugin leaves in a directory it patched through Steam."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import bundle
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
    optiscaler_version: str | None,
    fsr4_variant: str | None,
    fsr4_upscaler_sha256: str | None,
    patched_at: str,
    steam_game: SteamGame | None = None,
) -> dict:
    """The marker's JSON payload; every patch writes one, a Steam patch also records the game."""
    variant = bundle.normalize_variant(fsr4_variant)
    return {
        "appid": steam_game.appid if steam_game else "",
        "game_name": steam_game.name if steam_game else "",
        "dll_name": dll_name,
        "target_dir": str(target_dir),
        "original_launch_options": steam_game.original_launch_options if steam_game else "",
        "backed_up_files": backed_up_files,
        "optiscaler_version": optiscaler_version,
        "fsr4_variant": variant,
        "fsr4_variant_label": bundle.FSR4_VARIANTS[variant]["label"],
        "fsr4_upscaler_sha256": fsr4_upscaler_sha256,
        "managed_files": [
            {
                "path": str(target_dir / bundle.FSR4_UPSCALER_FILENAME),
                "sha256": fsr4_upscaler_sha256,
                "kind": "fsr4-upscaler",
                "variant": variant,
            }
        ],
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
