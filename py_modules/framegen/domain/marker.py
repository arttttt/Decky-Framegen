"""The FRAMEGEN_PATCH marker the plugin leaves in a directory it patched through Steam."""

from __future__ import annotations

from pathlib import Path

from . import bundle
from .launch_options import is_managed


def build(
    *,
    appid: str,
    game_name: str,
    dll_name: str,
    target_dir: Path,
    original_launch_options: str,
    backed_up_files: list[str],
    optiscaler_version: str | None,
    fsr4_variant: str | None,
    fsr4_upscaler_sha256: str | None,
    patched_at: str,
) -> dict:
    """The marker's JSON payload."""
    variant = bundle.normalize_variant(fsr4_variant)
    return {
        "appid": str(appid),
        "game_name": game_name,
        "dll_name": dll_name,
        "target_dir": str(target_dir),
        "original_launch_options": original_launch_options,
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
