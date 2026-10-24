"""File names the plugin works with, and what the plugin it continues put into games.

The proxy DLL names, the marker, the plugin's home (~/deckyscaler) with the scripts and core it keeps
there, and the tables of files the original Decky Framegen (and this plugin before its patch record)
placed in game directories, which resetting such a game to stock relies on. OptiScaler versions
themselves are described by domain/library.py.
"""


from __future__ import annotations

HOME_DIRNAME = "deckyscaler"
"""The plugin's home under the user's: the OptiScaler library, settings, patch index, core and scripts."""

FSR4_UPSCALER_FILENAME = "amd_fidelityfx_upscaler_dx12.dll"
FSR4_DRIVER_OVERRIDE_FILENAME = "amdxcffx64.dll"
VARIANT_EXTRA_FILENAMES = ["amdxc64.dll", FSR4_DRIVER_OVERRIDE_FILENAME]
"""Driver DLLs the original Decky Framegen placed for some FSR 4 variants."""

PROXY_DLLS = {
    "dxgi.dll": "Works for most DX12 games. Default.",
    "winmm.dll": "Use when dxgi.dll conflicts with an existing game file.",
    "version.dll": "Common fallback; works well with many launchers.",
    "dbghelp.dll": "Use for debug helper hook paths.",
    "winhttp.dll": "Use when other DLL names conflict.",
    "wininet.dll": "Use when other DLL names conflict.",
    "OptiScaler.asi": "For ASI loaders. Requires an ASI loader already installed in the game.",
}
"""The names OptiScaler.dll can be placed under, in the order the panel offers them, and when to pick each."""
PROXY_DLL_BACKUPS = list(PROXY_DLLS)

VALID_DLL_NAMES = set(PROXY_DLL_BACKUPS)
DEFAULT_PROXY_DLL = "dxgi.dll"

# What the original Decky Framegen placed, for resetting games it patched.
INJECTOR_FILENAMES = [
    *PROXY_DLL_BACKUPS,
    "nvngx.dll",
    "_nvngx.dll",
    "nvngx-wrapper.dll",
    "dlss-enabler.dll",
    "OptiScaler.dll",
]

# Game DLLs the patch replaces: backed up before patching, restored on unpatch.
ORIGINAL_DLL_BACKUPS = [
    "d3dcompiler_47.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    FSR4_UPSCALER_FILENAME,
    FSR4_DRIVER_OVERRIDE_FILENAME,
    "amdxc64.dll",
    "amd_fidelityfx_vk.dll",
    # Many games ship their own XeSS runtime next to the executable.
    "libxess.dll",
    "libxess_dx11.dll",
    "libxess_fg.dll",
    "libxell.dll",
]

RESTORABLE_BACKUP_FILES = [
    *PROXY_DLL_BACKUPS,
    *ORIGINAL_DLL_BACKUPS,
]

SUPPORT_FILES = [
    "libxess.dll",
    "libxess_dx11.dll",
    "libxess_fg.dll",
    "libxell.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    "amd_fidelityfx_vk.dll",
    "dlssg_to_fsr3_amd_is_better.dll",
    "fakenvapi.dll",
    "fakenvapi.ini",
]

MARKER_FILENAME = "DECKYSCALER_PATCH"
"""The marker a patch leaves in the directory it patched, holding its record."""
UPSTREAM_MARKER_FILENAME = "FRAMEGEN_PATCH"
"""The marker the original Decky Framegen left: a game it patched is reset, not unpatched by a record."""

LEGACY_FILES = [
    "dlssg_to_fsr3.ini",
    "dlssg_to_fsr3.log",
    "nvapi64.dll",
    "nvapi64.dll.b",
    "fakenvapi.log",
    "dlss-enabler.dll",
    "dlss-enabler-upscaler.dll",
    "dlss-enabler.log",
    "nvngx.ini",
    "nvngx-wrapper.dll",
    "_nvngx.dll",
    "dlssg_to_fsr3_amd_is_better-3.0.dll",
    "OptiScaler.asi",
    "OptiScaler.ini",
    "OptiScaler.log",
]


# Scripts from the plugin's assets/ installed into ~/deckyscaler, by installed name.
LAUNCHER_SCRIPTS = {
    "patch": "patch.sh",
    "unpatch": "unpatch.sh",
}

OPTIPATCHER_TARGET = "plugins/OptiPatcher.asi"

# The plugin's Python core, copied into ~/deckyscaler so the launch wrappers can run it.
CORE_PACKAGE = "deckyscaler"
