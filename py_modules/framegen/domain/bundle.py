"""What an installed OptiScaler bundle consists of.

The bundled release assets and their hashes, the FSR4 runtime variants and the
files each one adds, and the file-name lists the patcher works with. Pure data
plus pure lookups over it — no filesystem access.
"""

from __future__ import annotations

from pathlib import Path

OPTISCALER_ARCHIVE_ASSET = {
    "name": "Optiscaler_0.9.4-final.20260718._MM.7z",
    "sha256": "575cb4df866116093df75af607e37fd70e10f5163e0f23fd5c804142e80ef0ad",
    "version": "0.9.4-final.20260718",
}

FSR4_INT8_ASSET = {
    "name": "amd_fidelityfx_upscaler_dx12.dll",
    "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
    "version": "4.0.2c",
}

FSR4_OFFICIAL_411_ASSET = {
    "name": "amdxcffx64.dll",
    "sha256": "a2b136b6affd35a49b141a936be935f7d5ddc8d8f9b8c9afbe62ff9ddb2538a0",
    "version": "4.1.1-official",
}

FSR4_VALVE_411_ASSET = {
    "name": "amdxcffx64_valve_2.3.0.2913.dll",
    "sha256": "4e7dc37aebea3a90e3d3cc43e24cb2b54176b2535315f20dbe63b3b7cfc56b1e",
    "version": "4.1.1-valve-2.3.0.2913",
}

AMDXC64_RDNA2_ASSET = {
    "name": "amdxc64.dll",
    "sha256": "a0a0af61d475e30a70966b3459f3793df772faf8f26ae3261d10554ff592cbd5",
    "version": "8.18.10.0474",
}

OPTISCALER_PRE10_ASSET = {
    "name": "OptiScaler_0.10.0-pre1.20260622_135940.dll",
    "sha256": "b374b19081cc066365d0c6da4808d768e16469b0cbdfc478b6e95999947d5364",
    "version": "0.10.0-pre1.20260622_135940",
}

OPTIPATCHER_ASSET = {
    "name": "OptiPatcher_rolling.asi",
    "sha256": "88b9e1be3559737cd205fdf5f2c8550cf1923fb1def4c603e5bf03c3e84131b1",
    "version": "rolling",
}

FSR4_UPSCALER_FILENAME = "amd_fidelityfx_upscaler_dx12.dll"
FSR4_DRIVER_OVERRIDE_FILENAME = "amdxcffx64.dll"
INSTALL_MANIFEST_FILENAME = "install-manifest.json"
VERSION_FILENAME = "version.txt"
DEFAULT_FSR4_VARIANT = "rdna23-int8"

FSR4_VARIANTS = {
    "rdna23-int8": {
        "label": "4.0.2c / RDNA2-3 compatibility",
        "dir_name": "fsr4-rdna2-3",
        "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
        "source_asset_name": FSR4_INT8_ASSET["name"],
        "source_version": FSR4_INT8_ASSET["version"],
        "uses_archive_native": False,
        "extra_files": [],
    },
    "rdna4-native": {
        "label": "4.1.1 SDK / RDNA3 dGPU + RDNA4",
        "dir_name": "fsr4-rdna4",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "extra_files": [],
    },
    "rdna34-official-411": {
        "label": "4.1.1 driver override / RDNA3-4",
        "dir_name": "fsr4-rdna3-4-official-411",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "extra_files": [
            {
                "name": FSR4_DRIVER_OVERRIDE_FILENAME,
                "sha256": FSR4_OFFICIAL_411_ASSET["sha256"],
                "source_asset_name": FSR4_OFFICIAL_411_ASSET["name"],
                "source_version": FSR4_OFFICIAL_411_ASSET["version"],
            }
        ],
        "config_overrides": {},
    },
    "rdna2-valve-411-pre10": {
        "label": "4.1.1 Valve RDNA2 compatibility",
        "dir_name": "fsr4-rdna2-valve-411-pre10",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "injector": {
            "name": "OptiScaler.dll",
            "sha256": OPTISCALER_PRE10_ASSET["sha256"],
            "source_asset_name": OPTISCALER_PRE10_ASSET["name"],
            "source_version": OPTISCALER_PRE10_ASSET["version"],
        },
        "extra_files": [
            {
                "name": FSR4_DRIVER_OVERRIDE_FILENAME,
                "sha256": FSR4_VALVE_411_ASSET["sha256"],
                "source_asset_name": FSR4_VALVE_411_ASSET["name"],
                "source_version": FSR4_VALVE_411_ASSET["version"],
            },
            {
                "name": "amdxc64.dll",
                "sha256": AMDXC64_RDNA2_ASSET["sha256"],
                "source_asset_name": AMDXC64_RDNA2_ASSET["name"],
                "source_version": AMDXC64_RDNA2_ASSET["version"],
            }
        ],
        "config_overrides": {
            "FSR.Fsr4ForceModel": "2",
            "Plugins.LoadCustomAmdxc64OnRdna2": "true",
        },
    },
}
VARIANT_EXTRA_FILENAMES = sorted(
    {
        extra_file["name"]
        for variant in FSR4_VARIANTS.values()
        for extra_file in variant.get("extra_files", [])
    }
)

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

INJECTOR_FILENAMES = [
    *PROXY_DLL_BACKUPS,
    "nvngx.dll",
    "_nvngx.dll",
    "nvngx-wrapper.dll",
    "dlss-enabler.dll",
    "OptiScaler.dll",
]

PATCH_CLEANUP_FILES = [
    *INJECTOR_FILENAMES,
    *VARIANT_EXTRA_FILENAMES,
    "nvapi64.dll",
    "nvapi64.dll.b",
    "nvngx.ini",
    "dlss-enabler-upscaler.dll",
    "fakenvapi.log",
    "OptiScaler.log",
    "dlssg_to_fsr3.log",
    "dlssg_to_fsr3_amd_is_better-3.0.dll",
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


def normalize_variant(fsr4_variant: str | None) -> str:
    """A known variant id, or the default for anything else."""
    variant = str(fsr4_variant or "").strip()
    return variant if variant in FSR4_VARIANTS else DEFAULT_FSR4_VARIANT


def select_variant(requested: str | None, manifest_default: str | None) -> str:
    """The variant to use: the requested one if valid, else the bundle's default, else the global default."""
    for candidate in (requested, manifest_default):
        variant = str(candidate or "").strip()
        if variant in FSR4_VARIANTS:
            return variant
    return DEFAULT_FSR4_VARIANT


def variant_info(fsr4_variant: str | None) -> dict:
    return FSR4_VARIANTS[normalize_variant(fsr4_variant)]


def variant_extra_files(fsr4_variant: str | None) -> list[dict]:
    return list(variant_info(fsr4_variant).get("extra_files") or [])


def variant_injector(fsr4_variant: str | None) -> dict | None:
    injector = variant_info(fsr4_variant).get("injector")
    return injector if isinstance(injector, dict) else None


def variant_config_overrides(fsr4_variant: str | None) -> dict:
    overrides = variant_info(fsr4_variant).get("config_overrides") or {}
    return dict(overrides) if isinstance(overrides, dict) else {}


def variant_dir(fgmod_path: Path, fsr4_variant: str | None) -> Path:
    return fgmod_path / variant_info(fsr4_variant)["dir_name"]


def variant_upscaler_path(fgmod_path: Path, fsr4_variant: str | None) -> Path:
    return variant_dir(fgmod_path, fsr4_variant) / FSR4_UPSCALER_FILENAME


def variant_extra_file_path(fgmod_path: Path, fsr4_variant: str | None, filename: str) -> Path:
    return variant_dir(fgmod_path, fsr4_variant) / filename


def variant_injector_path(fgmod_path: Path, fsr4_variant: str | None) -> Path | None:
    injector = variant_injector(fsr4_variant)
    if not injector:
        return None
    return variant_dir(fgmod_path, fsr4_variant) / injector.get("name", "OptiScaler.dll")


def variant_renamed_proxy_path(fgmod_path: Path, fsr4_variant: str | None, dll_name: str) -> Path | None:
    if not variant_injector(fsr4_variant):
        return None
    return variant_dir(fgmod_path, fsr4_variant) / "renames" / dll_name


def detect_variant(upscaler_sha256: str | None, file_sha256: dict[str, str]) -> str | None:
    """Which FSR4 variant a patched directory carries, from the hashes of its files.

    `file_sha256` maps the variant extra-file names present in the directory to
    their hashes. Variants with extra files must match the upscaler and every
    extra file; otherwise the upscaler alone identifies the variant.
    """
    if not upscaler_sha256:
        return None
    upscaler = upscaler_sha256.lower()
    for variant_id, variant in FSR4_VARIANTS.items():
        extra_files = variant.get("extra_files") or []
        if not extra_files or str(variant.get("sha256") or "").lower() != upscaler:
            continue
        if all(file_sha256.get(extra["name"], "").lower() == extra["sha256"].lower() for extra in extra_files):
            return variant_id
    for variant_id, variant in FSR4_VARIANTS.items():
        if not variant.get("extra_files") and str(variant.get("sha256") or "").lower() == upscaler:
            return variant_id
    return None


# ── installing the bundle ────────────────────────────────────────────────────

# Every asset the plugin ships in bin/, verified by hash before installing.
RELEASE_ASSETS = (
    OPTISCALER_ARCHIVE_ASSET,
    FSR4_INT8_ASSET,
    FSR4_OFFICIAL_411_ASSET,
    FSR4_VALVE_411_ASSET,
    AMDXC64_RDNA2_ASSET,
    OPTISCALER_PRE10_ASSET,
    OPTIPATCHER_ASSET,
)

# Scripts from the plugin's assets/ installed into ~/fgmod, by installed name.
LAUNCHER_SCRIPTS = {
    "fgmod": "fgmod.sh",
    "fgmod-uninstaller.sh": "fgmod-uninstaller.sh",
    "update-optiscaler-config.py": "update-optiscaler-config.py",
}

OPTIPATCHER_TARGET = "plugins/OptiPatcher.asi"

# The plugin's Python core, copied into ~/fgmod so the launch wrappers can run it.
CORE_PACKAGE = "framegen"


def required_install_paths() -> list[str]:
    """Paths (relative to ~/fgmod) a complete install must contain."""
    paths = [
        "OptiScaler.dll",
        "OptiScaler.ini",
        FSR4_UPSCALER_FILENAME,
        *SUPPORT_FILES,
        *LAUNCHER_SCRIPTS,
        INSTALL_MANIFEST_FILENAME,
        OPTIPATCHER_TARGET,
        f"{CORE_PACKAGE}/__main__.py",
    ]
    for variant in FSR4_VARIANTS.values():
        variant_dir = variant["dir_name"]
        paths.append(f"{variant_dir}/{FSR4_UPSCALER_FILENAME}")
        injector = variant.get("injector")
        if isinstance(injector, dict):
            paths.append(f"{variant_dir}/{injector.get('name', 'OptiScaler.dll')}")
            paths.append(f"{variant_dir}/renames/dxgi.dll")
        paths.extend(f"{variant_dir}/{extra['name']}" for extra in variant.get("extra_files", []))
    return paths


def install_manifest(
    *,
    selected_variant: str,
    native_upscaler_sha256: str,
    optipatcher_sha256: str,
    active_upscaler_sha256: str,
    installed_at: str,
) -> dict:
    """The install-manifest.json written into ~/fgmod."""

    def located(entry: dict, variant_dir: str) -> dict:
        return {
            "name": entry["name"],
            "sha256": entry["sha256"],
            "source_asset_name": entry["source_asset_name"],
            "source_version": entry["source_version"],
            "path": f"{variant_dir}/{entry['name']}",
        }

    return {
        "schema_version": 1,
        "installed_at": installed_at,
        "optiscaler": {
            "asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
            "version": OPTISCALER_ARCHIVE_ASSET["version"],
            "sha256": OPTISCALER_ARCHIVE_ASSET["sha256"],
            "native_upscaler_sha256": native_upscaler_sha256,
        },
        "optipatcher": {
            "asset_name": OPTIPATCHER_ASSET["name"],
            "version": OPTIPATCHER_ASSET["version"],
            "sha256": optipatcher_sha256,
            "target_path": OPTIPATCHER_TARGET,
        },
        "fsr4_variants": {
            variant_id: {
                "label": variant["label"],
                "dir_name": variant["dir_name"],
                "path": f"{variant['dir_name']}/{FSR4_UPSCALER_FILENAME}",
                "sha256": variant["sha256"],
                "source_asset_name": variant["source_asset_name"],
                "source_version": variant["source_version"],
                "uses_archive_native": bool(variant["uses_archive_native"]),
                "injector": (
                    located(variant["injector"], variant["dir_name"])
                    if isinstance(variant.get("injector"), dict)
                    else None
                ),
                "config_overrides": dict(variant.get("config_overrides") or {}),
                "extra_files": [located(extra, variant["dir_name"]) for extra in variant.get("extra_files", [])],
            }
            for variant_id, variant in FSR4_VARIANTS.items()
        },
        "selected_default_variant": selected_variant,
        "active_root_upscaler": {
            "path": FSR4_UPSCALER_FILENAME,
            "sha256": active_upscaler_sha256,
            "variant": selected_variant,
        },
    }
