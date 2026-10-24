"""The plugin's own files in ~/deckyscaler: its Python core and the launch scripts Steam runs."""

from __future__ import annotations

import shutil
from pathlib import Path

from deckyscaler.domain import bundle

CORE_SOURCE = Path(__file__).resolve().parents[1]
"""The deckyscaler package this plugin runs; ~/deckyscaler gets a copy so the launch scripts can run it."""


def refresh_core(plugin_home: Path, assets_dir: Path) -> None:
    """Copy the core and the launch scripts into ~/deckyscaler, each replacing the old one by renaming.

    A game launched meanwhile reads either the old script or the new one, never half of one.
    """
    plugin_home.mkdir(parents=True, exist_ok=True)
    for installed_name, source_name in bundle.LAUNCHER_SCRIPTS.items():
        source = assets_dir / source_name
        if source.exists():
            staged = plugin_home / f".{installed_name}.new"
            shutil.copy2(source, staged)
            staged.chmod(0o755)
            staged.replace(plugin_home / installed_name)

    core = plugin_home / bundle.CORE_PACKAGE
    staged, retired = plugin_home / f".{bundle.CORE_PACKAGE}.new", plugin_home / f".{bundle.CORE_PACKAGE}.old"
    for leftover in (staged, retired):
        shutil.rmtree(leftover, ignore_errors=True)
    shutil.copytree(CORE_SOURCE, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if core.exists():
        core.replace(retired)
    staged.replace(core)
    shutil.rmtree(retired, ignore_errors=True)
