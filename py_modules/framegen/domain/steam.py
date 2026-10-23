"""Reading Steam's library metadata: where libraries live and which games they hold."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_FLATPAK_HOME = Path(".var") / "app" / "com.valvesoftware.Steam" / "home"

# Steam installs these as apps, but they are tools, not games.
_TOOL_NAME_MARKERS = ("Proton", "Steam Linux Runtime")


@dataclass(frozen=True)
class AppManifest:
    appid: str
    name: str
    installdir: str


def steam_root_candidates(home: Path) -> list[Path]:
    """Where a Steam install may live: native layouts first, then the Flatpak sandbox."""
    return [
        home / ".local" / "share" / "Steam",
        home / ".steam" / "steam",
        home / ".steam" / "root",
        home / _FLATPAK_HOME / ".local" / "share" / "Steam",
        home / _FLATPAK_HOME / ".steam" / "steam",
    ]


def _quoted_value(line: str, key: str) -> str:
    return line.split(f'"{key}"', 1)[1].strip().strip('"')


def parse_library_folders(text: str) -> list[str]:
    """Library paths listed in a libraryfolders.vdf."""
    return [
        _quoted_value(line, "path").replace("\\\\", "/")
        for line in text.splitlines()
        if '"path"' in line
    ]


def parse_app_manifest(text: str) -> AppManifest:
    """The fields of an appmanifest_*.acf the plugin uses; missing ones are empty."""
    fields = {"appid": "", "name": "", "installdir": ""}
    for line in text.splitlines():
        for key in fields:
            if f'"{key}"' in line:
                fields[key] = _quoted_value(line, key)
                break
    return AppManifest(**fields)


def is_game(manifest: AppManifest) -> bool:
    """A manifest describes a game the plugin can patch: complete, and not a Steam tool."""
    if not manifest.appid or not manifest.name:
        return False
    return not any(marker in manifest.name for marker in _TOOL_NAME_MARKERS)
