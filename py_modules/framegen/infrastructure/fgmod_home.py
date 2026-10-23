"""The plugin's own files in ~/fgmod: its Python core and the launch scripts Steam runs."""

from __future__ import annotations

import shutil
from pathlib import Path

from framegen.domain import bundle

CORE_SOURCE = Path(__file__).resolve().parents[1]
"""The framegen package this plugin runs; ~/fgmod gets a copy so the launch scripts can run it."""


def refresh_core(fgmod: Path, assets_dir: Path) -> None:
    """Copy the core and the launch scripts into ~/fgmod, each replacing the old one by renaming.

    A game launched meanwhile reads either the old script or the new one, never half of one.
    """
    fgmod.mkdir(parents=True, exist_ok=True)
    for installed_name, source_name in bundle.LAUNCHER_SCRIPTS.items():
        source = assets_dir / source_name
        if source.exists():
            staged = fgmod / f".{installed_name}.new"
            shutil.copy2(source, staged)
            staged.chmod(0o755)
            staged.replace(fgmod / installed_name)

    core = fgmod / bundle.CORE_PACKAGE
    staged, retired = fgmod / f".{bundle.CORE_PACKAGE}.new", fgmod / f".{bundle.CORE_PACKAGE}.old"
    for leftover in (staged, retired):
        shutil.rmtree(leftover, ignore_errors=True)
    shutil.copytree(CORE_SOURCE, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    if core.exists():
        core.replace(retired)
    staged.replace(core)
    shutil.rmtree(retired, ignore_errors=True)
