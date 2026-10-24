"""File names the plugin works with, and what its earlier versions put into games.

The proxy DLL names, the marker, the scripts and core it keeps in ~/fgmod, and the tables of
files earlier plugin versions placed in game directories, which resetting such a game to stock
relies on. OptiScaler versions themselves are described by domain/library.py.
"""

from __future__ import annotations

FSR4_UPSCALER_FILENAME = "amd_fidelityfx_upscaler_dx12.dll"
FSR4_DRIVER_OVERRIDE_FILENAME = "amdxcffx64.dll"
VARIANT_EXTRA_FILENAMES = ["amdxc64.dll", FSR4_DRIVER_OVERRIDE_FILENAME]
"""Driver DLLs earlier versions placed for some FSR 4 variants."""

PROXY_DLL_BACKUPS = [
    "dxgi.dll",
    "winmm.dll",
    "dbghelp.dll",
    "version.dll",
    "wininet.dll",
    "winhttp.dll",
    "OptiScaler.asi",
]

VALID_DLL_NAMES = set(PROXY_DLL_BACKUPS)
DEFAULT_PROXY_DLL = "dxgi.dll"

# What earlier plugin versions placed, for resetting games they patched.
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

MARKER_FILENAME = "FRAMEGEN_PATCH"

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


# Scripts from the plugin's assets/ installed into ~/fgmod, by installed name.
LAUNCHER_SCRIPTS = {
    "fgmod": "fgmod.sh",
    "fgmod-uninstaller.sh": "fgmod-uninstaller.sh",
    "update-optiscaler-config.py": "update-optiscaler-config.py",
}

OPTIPATCHER_TARGET = "plugins/OptiPatcher.asi"

# The plugin's Python core, copied into ~/fgmod so the launch wrappers can run it.
CORE_PACKAGE = "framegen"
