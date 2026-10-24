"""Reading what decides FSR 4 under Proton from disk: Steam's tool choice, the tool, the game's prefix, the GPU."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar

from deckyscaler.domain import fsr4, keyvalues, steam

log = logging.getLogger(__name__)

SYSFS = Path("/sys")
SYSTEM_TOOLS = Path("/usr/share/steam/compatibilitytools.d")
"""Where distributions install compatibility tools for every user, next to each Steam root's own."""


T = TypeVar("T")
_cache: dict[tuple[str, Path], tuple[int, object]] = {}


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _cached(kind: str, path: Path, compute: Callable[[], T]) -> T:
    """`compute()`'s result for `path`, kept while the file's mtime stays: config.vdf runs to megabytes and a
    tool's protonfixes to tens, read on every status of every game otherwise."""
    try:
        stamp = path.stat().st_mtime_ns
    except OSError:
        return compute()
    hit = _cache.get((kind, path))
    if hit is not None and hit[0] == stamp:
        return hit[1]  # type: ignore[return-value]
    value = compute()
    _cache[(kind, path)] = (stamp, value)
    return value


def _steam_roots(home: Path) -> list[Path]:
    return [root for root in steam.steam_root_candidates(home) if root.is_dir()]


def compat_tool(home: Path, appid: str) -> str | None:
    """The Proton Steam runs the game with, from the first Steam root that has a config.vdf."""
    for root in _steam_roots(home):
        config = root / "config" / "config.vdf"
        if config.is_file():
            return fsr4.compat_tool(_cached("config", config, lambda: keyvalues.parse(_read(config))), appid)
    return None


def tool_directory(home: Path, name: str) -> Path | None:
    """A custom tool's directory (compatibilitytools.d), found by the internal name its manifest declares.
    Valve's own Protons live elsewhere and have no FSR 4 upgrade, so they are not looked up."""
    tool_dirs = [root / "compatibilitytools.d" for root in _steam_roots(home)] + [SYSTEM_TOOLS]
    for tools in tool_dirs:
        if not tools.is_dir():
            continue
        for manifest in sorted(tools.glob("*/compatibilitytool.vdf")):
            tools = _cached("tools", manifest, lambda manifest=manifest: fsr4.custom_tools(keyvalues.parse(_read(manifest))))
            install_path = tools.get(name.lower())
            if install_path is not None:
                return (manifest.parent / install_path).resolve()
    return None


def reads_upgrade_variable(tool: Path) -> bool:
    """Whether the tool's proton script or its protonfixes read the FSR 4 upgrade variable. A tool is
    replaced as a whole when it updates, so its proton script's mtime stands for all of it."""

    def scan() -> bool:
        sources = [tool / "proton", *sorted(tool.glob("protonfixes/**/*.py"))]
        return any(fsr4.reads_upgrade_variable(_read(source)) for source in sources if source.is_file())

    return _cached("reads-variable", tool / "proton", scan)


def compatdata(game_library: Path, appid: str) -> Path:
    return game_library / "steamapps" / "compatdata" / str(appid)


def prefix_dll(game_compatdata: Path) -> Path:
    """Where the game's Proton puts AMD's FSR 4 driver DLL."""
    return game_compatdata / fsr4.PREFIX_DLL


def dll_in_prefix(game_compatdata: Path) -> bool:
    return prefix_dll(game_compatdata).is_file()


def tracked_version(game_compatdata: Path) -> str | None:
    return fsr4.tracked_version(_read(game_compatdata / fsr4.TRACKING_FILE))


def amd_gpu() -> bool:
    """Whether the GPU games render on is AMD's: the boot VGA device when the machine says which, else any GPU."""
    cards = [
        card / "device"
        for card in sorted(SYSFS.glob("class/drm/card*"))
        if card.name[4:].isdigit() and (card / "device" / "vendor").is_file()  # not connectors like card1-DP-1
    ]
    boot = [card for card in cards if _read(card / "boot_vga").strip() == "1"]
    return any(fsr4.is_amd(_read(card / "vendor")) for card in boot or cards)
