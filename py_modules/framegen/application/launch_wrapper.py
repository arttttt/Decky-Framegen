"""What the ~/fgmod launch wrappers do before starting a game: find its directory, then patch or unpatch it."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path

from framegen.application.patcher import Patcher
from framegen.domain import launch_target
from framegen.infrastructure import game_locator

log = logging.getLogger(__name__)


class WrapperError(Exception):
    """The wrapper cannot proceed; the message is shown to the user."""


class LaunchWrapper:
    def __init__(self, home: Path, environ: Mapping[str, str]):
        self.home = home
        self.environ = environ
        self.patcher = Patcher(home)

    def locate(self, command: list[str]) -> Path:
        """The directory to patch for a launch command, checked to exist and be writable."""
        found = launch_target.game_dir_from_command(command)
        lutris_id = launch_target.lutris_game_id(command)
        if lutris_id:
            lutris_dir = game_locator.lutris_game_dir(lutris_id, self.home)
            if lutris_dir:
                found = str(lutris_dir)
        if not found:
            found = self.environ.get("STEAM_COMPAT_INSTALL_PATH") or None
        directory = Path(found) if found else None
        if directory and (directory / "Engine").is_dir():
            directory = game_locator.unreal_binaries_dir(directory) or directory
        if directory is None or not directory.is_dir():
            raise WrapperError("Could not resolve game directory!")
        if not os.access(directory, os.W_OK):
            raise WrapperError("No write permission to the game folder!")
        log.info(f"Target directory: {directory}")
        return directory

    def patch(self, command: list[str], dll_name: str, fsr4_variant: str, reset_ini: bool = False) -> Path:
        directory = self.locate(command)
        result = self.patcher.patch_directory(directory, dll_name, fsr4_variant, reset_ini=reset_ini)
        if result["status"] != "success":
            raise WrapperError(result["message"])
        return directory

    def unpatch(self, command: list[str]) -> Path:
        directory = self.locate(command)
        result = self.patcher.unpatch_directory(directory)
        if result["status"] != "success":
            raise WrapperError(result["message"])
        return directory
