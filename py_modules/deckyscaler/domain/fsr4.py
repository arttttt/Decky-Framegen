"""FSR 4 under Proton: whether a game gets AMD's FSR 4 driver DLL, and how to ask Proton for it.

On Linux FSR 4 needs amdxcffx64.dll, which neither OptiScaler's archives nor Valve's Proton ship.
Proton builds with protonfixes' upscaler support (GE-Proton, Proton-CachyOS, Proton-EM) download it
into the game's prefix on launch when UPGRADE_VARIABLE is set, and record its version in the
game's compatdata/upscaler_files. OptiScaler then finds it and offers FSR 4.
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from . import keyvalues

AMD_VENDOR = "0x1002"
UPGRADE_VARIABLE = "PROTON_FSR4_UPGRADE"
"""What a Proton build with upscaler support reads to fetch FSR 4; current GE-Proton covers RDNA 3 with it too."""
DLL = "amdxcffx64.dll"
PREFIX_DLL = f"pfx/drive_c/windows/system32/{DLL}"
"""Where the DLL lands, relative to the game's compatdata directory."""
TRACKING_FILE = "upscaler_files"
_TRACKED_DLL = f"drive_c/windows/system32/{DLL}"
GLOBAL_MAPPING = "0"
"""CompatToolMapping's entry for the tool the user chose for every game."""

IN_PREFIX = "in-prefix"
WILL_FETCH = "will-fetch"
UNSUPPORTED = "unsupported"


def is_amd(vendor: str) -> bool:
    """Whether a PCI vendor id (as sysfs gives it, e.g. "0x1002\\n") is AMD's."""
    return vendor.strip().lower() == AMD_VENDOR


def compat_tool(config: keyvalues.KeyValues, appid: str) -> str | None:
    """The compatibility tool Steam runs a game with, by internal name (GE-Proton11-11, proton_experimental):
    the game's own choice, else the one chosen for every game. None means Steam's default, which no file names."""
    mapping = keyvalues.find(config, "InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping")
    if not isinstance(mapping, dict):
        return None
    for key in (str(appid), GLOBAL_MAPPING):
        entry = mapping.get(key)
        name = entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str) and name:
            return name
    return None


def custom_tools(manifest: keyvalues.KeyValues) -> dict[str, str]:
    """The tools a compatibilitytool.vdf declares: internal name, lowercased as Steam compares it → install_path
    (relative to the file)."""
    tools = keyvalues.find(manifest, "compatibilitytools", "compat_tools")
    if not isinstance(tools, dict):
        return {}
    return {
        name: str(entry.get("install_path") or ".")
        for name, entry in tools.items()
        if isinstance(entry, dict)
    }


def reads_upgrade_variable(source: str) -> bool:
    """Whether a Proton build's script or protonfixes code reads the FSR 4 upgrade variable."""
    return UPGRADE_VARIABLE in source


def tracked_version(tracking: str) -> str | None:
    """The FSR 4 DLL's version protonfixes recorded in upscaler_files, or None."""
    try:
        data = json.loads(tracking)
    except ValueError:
        return None
    entry = data.get("fsr4_files", {}).get(_TRACKED_DLL) if isinstance(data, dict) else None
    version = entry.get("version") if isinstance(entry, dict) else None
    return str(version) if version else None


@dataclass(frozen=True)
class State:
    """A game's FSR 4 under Proton: the DLL is in its prefix (with the version when recorded), its
    Proton will fetch it on launch, or its Proton can't. `tool` is the Proton's name, None for Steam's default."""

    kind: str
    tool: str | None
    version: str | None = None


def state(amd_gpu: bool, tool: str | None, tool_reads_variable: bool, dll_in_prefix: bool, version: str | None) -> State | None:
    """What to tell the user about FSR 4 for a game; None off AMD, where FSR 4 isn't the question."""
    if not amd_gpu:
        return None
    if dll_in_prefix:
        return State(IN_PREFIX, tool, version)
    if tool_reads_variable:
        return State(WILL_FETCH, tool)
    return State(UNSUPPORTED, tool)


def wants_upgrade_variable(amd_gpu: bool, tool_reads_variable: bool) -> bool:
    """Whether a patch adds UPGRADE_VARIABLE to the game's launch options."""
    return amd_gpu and tool_reads_variable
