"""Filesystem and Lutris lookups for finding a game directory from its launch command."""

from __future__ import annotations

import fnmatch
import json
import logging
import shutil
import subprocess
from pathlib import Path

from framegen.domain import launch_target

log = logging.getLogger(__name__)


def unreal_binaries_dir(root: Path) -> Path | None:
    """For an Unreal Engine install, the directory of `<Project>/Binaries/Win64/<Game>.exe`."""
    for candidate in sorted(root.glob("*/*/*/*")):
        path = str(candidate)
        if fnmatch.fnmatch(path, launch_target.UNREAL_BINARY_PATTERN) and "/Engine/" not in path:
            return candidate.parent
    return None


def lutris_game_dir(game_id: str, home: Path) -> Path | None:
    """The directory of a Lutris game's executable, from `lutris --list-games` and its YAML config."""
    if shutil.which("lutris") is None:
        log.info("Lutris launch command, but lutris is not installed")
        return None
    try:
        listing = subprocess.run(["lutris", "--list-games", "--json"], capture_output=True, text=True, check=False)
        games = json.loads(listing.stdout or "[]")
    except (OSError, ValueError) as exc:
        log.error(f"Could not list Lutris games: {exc}")
        return None
    slug = next((game.get("slug") for game in games if str(game.get("id")) == game_id), None)
    if not slug:
        log.info(f"Could not find slug for Lutris ID {game_id}")
        return None
    configs = sorted(
        path
        for path in (home / ".config" / "lutris" / "games").glob("*.yml")
        if path.name.lower().startswith(f"{slug.lower()}-")
    )
    if not configs:
        log.info(f"No config file found for slug '{slug}'")
        return None
    exe = launch_target.lutris_exe(configs[0].read_text(encoding="utf-8", errors="replace"))
    if not exe:
        log.info(f"Executable path not found in {configs[0]}")
        return None
    return Path(launch_target.dirname(exe))
