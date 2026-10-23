"""Reading what is installed in ~/fgmod: its manifest and OptiScaler version."""

from __future__ import annotations

from pathlib import Path

from framegen.domain import bundle
from framegen.infrastructure import files


def manifest_path(fgmod_path: Path) -> Path:
    return fgmod_path / bundle.INSTALL_MANIFEST_FILENAME


def load_manifest(fgmod_path: Path) -> dict:
    return files.read_json(manifest_path(fgmod_path))


def selected_variant(fgmod_path: Path, requested: str | None = None) -> str:
    """The requested variant if valid, else the installed bundle's default, else the global default."""
    return bundle.select_variant(requested, load_manifest(fgmod_path).get("selected_default_variant"))


def optiscaler_version(fgmod_path: Path) -> str | None:
    """The installed OptiScaler version: from the manifest, else from version.txt (older installs)."""
    optiscaler = load_manifest(fgmod_path).get("optiscaler")
    if isinstance(optiscaler, dict) and optiscaler.get("version"):
        return str(optiscaler["version"])
    version_file = fgmod_path / bundle.VERSION_FILENAME
    try:
        if version_file.exists():
            return version_file.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None
    return None
