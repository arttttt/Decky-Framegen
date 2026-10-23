"""Finding the game directory from the command a launcher runs (`<wrapper> %command%`).

Steam passes the game's command line to the wrapper; for some games the .exe it
names is a launcher, and the real binary — where the proxy DLL must go — lives
elsewhere in the install.
"""

from __future__ import annotations

import posixpath
import re

# (substring identifying the game, launcher path fragment, real binary fragment)
LAUNCHER_REMAPS = (
    ("Cyberpunk 2077", "REDprelauncher.exe", "bin/x64/Cyberpunk2077.exe"),
    ("Witcher 3", "REDprelauncher.exe", "bin/x64_dx12/witcher3.exe"),
    ("Baldurs Gate 3", "Launcher/LariLauncher.exe", "bin/bg3_dx11.exe"),
    ("HITMAN 3", "Launcher.exe", "Retail/HITMAN3.exe"),
    ("HITMAN World of Assassination", "Launcher.exe", "Retail/HITMAN3.exe"),
    ("SYNCED", "Launcher/sop_launcher.exe", "SYNCED.exe"),
    ("2KLauncher", "2KLauncher/LauncherPatcher.exe", "DoesntMatter.exe"),
    ("Warhammer 40,000 DARKTIDE", "launcher/Launcher.exe", "binaries/Darktide.exe"),
    ("Warhammer Vermintide 2", "launcher/Launcher.exe", "binaries_dx12/vermintide2_dx12.exe"),
    ("Satisfactory", "FactoryGameSteam.exe", "Engine/Binaries/Win64/FactoryGameSteam-Win64-Shipping.exe"),
    ("FINAL FANTASY XIV Online", "boot/ffxivboot.exe", "game/ffxiv_dx11.exe"),
)

LUTRIS_PREFIX = "lutris:rungameid/"

# Unreal Engine games keep the real binary at <root>/<Project>/Binaries/Win64/<Game>.exe.
UNREAL_BINARY_PATTERN = "*Binaries/Win64/*.exe"


def dirname(path: str) -> str:
    """The directory part of a path, as the `dirname` command gives it ("." for a bare name)."""
    stripped = path.rstrip("/") or "/"
    return posixpath.dirname(stripped) or "."


def remap_launcher(exe_path: str) -> str:
    """Replace a known launcher in an executable path with the game binary it starts."""
    for marker, launcher, binary in LAUNCHER_REMAPS:
        if marker in exe_path:
            exe_path = exe_path.replace(launcher, binary)
    return exe_path


def game_dir_from_command(args: list[str]) -> str | None:
    """The game directory named by a launch command, before Lutris and fallbacks.

    A single argument is the game's .exe or its directory; in a full command
    line the first .exe argument (with launchers remapped) decides.
    """
    if len(args) == 1:
        return dirname(args[0]) if args[0].endswith(".exe") else args[0]
    for arg in args:
        if arg.endswith(".exe"):
            return dirname(remap_launcher(arg))
    return None


def lutris_game_id(args: list[str]) -> str | None:
    """The Lutris game id in a `lutris:rungameid/<id>` launch command."""
    for arg in args:
        if arg.startswith(LUTRIS_PREFIX):
            return arg[len(LUTRIS_PREFIX) :]
    return None


def lutris_exe(game_config: str) -> str | None:
    """The `exe:` entry of a Lutris game's YAML config."""
    for line in game_config.splitlines():
        if re.match(r"^\s*exe:", line):
            return re.sub(r".*exe:\s*", "", line, count=1) or None
    return None
