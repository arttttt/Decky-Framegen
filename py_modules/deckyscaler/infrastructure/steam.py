"""Finding Steam libraries, installed games and their executables on disk."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from deckyscaler.domain import steam

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class InstalledGame:
    appid: str
    name: str
    library_path: Path
    install_path: Path


def library_paths(home: Path) -> list[Path]:
    """Every Steam library: each existing Steam root plus the folders its libraryfolders.vdf lists."""
    paths: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        if str(path) not in seen:
            paths.append(path)
            seen.add(str(path))

    for steam_root in steam.steam_root_candidates(home):
        if steam_root.exists():
            add(steam_root)
        library_file = steam_root / "steamapps" / "libraryfolders.vdf"
        if not library_file.exists():
            continue
        try:
            text = library_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            log.error(f"[DeckyScaler] failed to parse libraryfolders: {library_file}: {exc}")
            continue
        for path in steam.parse_library_folders(text):
            add(Path(path))
    return paths


def installed_games(home: Path, appid: str | None = None) -> list[InstalledGame]:
    """Installed games across all libraries, sorted by name; one entry per appid (the last found wins)."""
    by_appid: dict[str, InstalledGame] = {}
    for library_path in library_paths(home):
        steamapps = library_path / "steamapps"
        if not steamapps.exists():
            continue
        for manifest_file in steamapps.glob("appmanifest_*.acf"):
            try:
                manifest = steam.parse_app_manifest(manifest_file.read_text(encoding="utf-8", errors="replace"))
            except OSError as exc:
                log.error(f"[DeckyScaler] skipping manifest {manifest_file}: {exc}")
                continue
            if not steam.is_game(manifest):
                continue
            if appid is not None and manifest.appid != str(appid):
                continue
            install_path = steamapps / "common" / manifest.installdir if manifest.installdir else Path()
            by_appid[manifest.appid] = InstalledGame(manifest.appid, manifest.name, library_path, install_path)
    return sorted(by_appid.values(), key=lambda game: game.name.lower())


def find_game(home: Path, appid: str) -> InstalledGame | None:
    matches = installed_games(home, appid)
    return matches[0] if matches else None


def executables(install_root: Path) -> list[Path]:
    """Every .exe file under a game's install directory."""
    if not install_root.exists():
        return []
    try:
        return [exe for exe in install_root.rglob("*.exe") if exe.is_file()]
    except OSError as exc:
        log.error(f"[DeckyScaler] exe scan failed for {install_root}: {exc}")
        return []
