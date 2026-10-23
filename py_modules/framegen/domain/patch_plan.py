"""What patching or unpatching a game directory does, as an ordered list of operations.

The planner is pure: it reads facts gathered from the game directory and the
installed bundle and returns operations; a service executes them. Names are
relative to the game directory; bundle sources are relative to ~/fgmod.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import bundle, ini

BACKUP_SUFFIX = ".b"
INI_FILENAME = "OptiScaler.ini"
PLUGINS_DIR = "plugins"
D3D12_DIR = "D3D12_Optiscaler"
UNINSTALLER_FILENAME = "fgmod-uninstaller.sh"
PLUGIN_FILES = frozenset({bundle.OPTIPATCHER_TARGET})
"""Files a patch has ever placed in the game's plugins/ directory."""
VALVE_VARIANT = "rdna2-valve-411-pre10"


# ── operations ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Move:
    source: str
    destination: str


@dataclass(frozen=True)
class DeleteFile:
    name: str


@dataclass(frozen=True)
class RemoveTree:
    name: str


@dataclass(frozen=True)
class RemoveFileOrTree:
    name: str


@dataclass(frozen=True)
class CopyFromBundle:
    source: str
    destination: str


@dataclass(frozen=True)
class MergeTreeFromBundle:
    name: str


@dataclass(frozen=True)
class EditIni:
    action: str
    transform: Callable[[str], str]


Operation = Move | DeleteFile | RemoveTree | RemoveFileOrTree | CopyFromBundle | MergeTreeFromBundle | EditIni


# ── facts ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GameDirectory:
    """What the planner needs to know about a game directory before it changes anything."""

    entries: frozenset[str]
    """Names present at the top level of the directory. None of them is the patch's: a repatch
    undoes the previous patch before planning."""
    previous_variant: str = ""
    """FSR4 variant recorded by the patch marker in this directory, if any."""


@dataclass(frozen=True)
class PatchRequest:
    dll_name: str
    variant: str
    """A known variant id (already selected)."""
    reset_ini: bool = False
    """Replace the game's OptiScaler.ini with the bundle's instead of keeping it."""


class PlanError(Exception):
    """The installed bundle cannot satisfy the request; the message is shown to the user."""


@dataclass(frozen=True)
class PatchPlan:
    operations: tuple[Operation, ...]
    upscaler_source: str


# ── patch ────────────────────────────────────────────────────────────────────


def injector_candidates(variant: str, dll_name: str) -> list[str]:
    """Where the proxy DLL is copied from, most specific first."""
    candidates = []
    injector = bundle.variant_injector(variant)
    if injector:
        variant_dir = bundle.variant_info(variant)["dir_name"]
        candidates.append(f"{variant_dir}/renames/{dll_name}")
        candidates.append(f"{variant_dir}/{injector.get('name', 'OptiScaler.dll')}")
    candidates.append(f"renames/{dll_name}")
    candidates.append("OptiScaler.dll")
    return candidates


def upscaler_source(variant: str, bundle_files: frozenset[str]) -> str:
    """The variant's FSR4 upscaler, falling back to the bundle's active one."""
    variant_upscaler = f"{bundle.variant_info(variant)['dir_name']}/{bundle.FSR4_UPSCALER_FILENAME}"
    if variant_upscaler in bundle_files:
        return variant_upscaler
    if bundle.FSR4_UPSCALER_FILENAME in bundle_files:
        return bundle.FSR4_UPSCALER_FILENAME
    raise PlanError(f"FSR4 upscaler variant not found for {variant}. Reinstall OptiScaler.")


def ini_overrides(variant: str, previous_variant: str) -> dict:
    """INI overrides for the variant; leaving the Valve variant resets the keys it set."""
    overrides = bundle.variant_config_overrides(variant)
    if previous_variant == VALVE_VARIANT and variant != previous_variant:
        overrides.setdefault("FSR.Fsr4ForceModel", "auto")
        overrides.setdefault("Plugins.LoadCustomAmdxc64OnRdna2", "false")
    return overrides


def plan_patch(game: GameDirectory, bundle_files: frozenset[str], request: PatchRequest) -> PatchPlan:
    """Back up what the game owns, clear stale patch files, then lay down the bundle."""
    if "OptiScaler.dll" not in bundle_files:
        raise PlanError("OptiScaler.dll not found in ~/fgmod. Reinstall OptiScaler.")
    upscaler = upscaler_source(request.variant, bundle_files)

    present = set(game.entries)
    operations: list[Operation] = []

    def move(source: str, destination: str) -> None:
        operations.append(Move(source, destination))
        present.discard(source)
        present.add(destination)

    def delete(name: str) -> None:
        operations.append(DeleteFile(name))
        present.discard(name)

    # 1. Proxy-named DLLs the game shipped are kept as backups.
    for name in bundle.PROXY_DLL_BACKUPS:
        if name in present and name + BACKUP_SUFFIX not in present:
            move(name, name + BACKUP_SUFFIX)

    # 2. Remove injectors and leftovers of earlier patches.
    for name in dict.fromkeys(bundle.PATCH_CLEANUP_FILES):
        if name in present:
            delete(name)

    # 3. Back up game DLLs the bundle replaces.
    for name in bundle.ORIGINAL_DLL_BACKUPS:
        if name in present and name + BACKUP_SUFFIX not in present:
            move(name, name + BACKUP_SUFFIX)

    # 4. The proxy DLL.
    injector = next(path for path in injector_candidates(request.variant, request.dll_name) if path in bundle_files)
    operations.append(CopyFromBundle(injector, request.dll_name))
    present.add(request.dll_name)

    # 5. The per-game INI: keep the user's (unless asked to reset it), otherwise start from the bundle's.
    if (request.reset_ini or INI_FILENAME not in present) and INI_FILENAME in bundle_files:
        operations.append(CopyFromBundle(INI_FILENAME, INI_FILENAME))
        present.add(INI_FILENAME)
    if INI_FILENAME in present:
        overrides = ini_overrides(request.variant, game.previous_variant)
        operations += [
            EditIni("migrate FGType to FGInput/FGOutput", ini.migrate_fgtype),
            EditIni("disable HQ font auto mode", ini.disable_hq_font_auto),
            EditIni("apply FSR4 variant overrides", lambda content: ini.apply_overrides(content, overrides)),
        ]

    # 6. Read-only directories OptiScaler loads from.
    operations += [MergeTreeFromBundle(name) for name in (PLUGINS_DIR, D3D12_DIR) if name in bundle_files]

    # 7. Support libraries, the variant's FSR4 upscaler and its extra driver DLLs.
    operations += [CopyFromBundle(name, name) for name in bundle.SUPPORT_FILES if name in bundle_files]
    operations.append(CopyFromBundle(upscaler, bundle.FSR4_UPSCALER_FILENAME))
    variant_dir = bundle.variant_info(request.variant)["dir_name"]
    for extra in bundle.variant_extra_files(request.variant):
        source = f"{variant_dir}/{extra['name']}"
        if source in bundle_files:
            operations.append(CopyFromBundle(source, extra["name"]))

    return PatchPlan(_preserving(tuple(operations), game.entries), upscaler)


def _preserving(operations: tuple[Operation, ...], entries: frozenset[str]) -> tuple[Operation, ...]:
    """The plan with every file that was in the directory kept as a backup before it is removed or overwritten.

    A repatch undoes the previous patch first, so whatever is in the directory now is not the
    patch's. The backup tables above name the usual cases; this makes it hold for every file.
    A file that already has a backup beside it keeps the old behaviour (the backup is the original).
    """
    present = set(entries)
    kept: list[Operation] = []
    for operation in operations:
        match operation:
            case Move(source, destination):
                present.discard(source)
                present.add(destination)
            case DeleteFile(name) if name in present and f"{name}{BACKUP_SUFFIX}" not in present:
                kept.append(Move(name, f"{name}{BACKUP_SUFFIX}"))
                present.discard(name)
                present.add(f"{name}{BACKUP_SUFFIX}")
                continue
            case DeleteFile(name):
                present.discard(name)
            case CopyFromBundle(_, destination) if destination in present and f"{destination}{BACKUP_SUFFIX}" not in present:
                kept.append(Move(destination, f"{destination}{BACKUP_SUFFIX}"))
                present.add(f"{destination}{BACKUP_SUFFIX}")
        kept.append(operation)
    return tuple(kept)


# ── unpatch ──────────────────────────────────────────────────────────────────


def plan_unpatch(entries: frozenset[str], plugin_entries: frozenset[str]) -> tuple[Operation, ...]:
    """Remove everything a patch may have placed, then restore the backups.

    `plugin_entries` lists the game's `plugins/` directory: only the files a patch puts
    there are removed, and the directory itself only when nothing else is left in it.
    A file with a backup is restored from it rather than deleted, whatever its era.
    """
    present = set(entries)
    operations: list[Operation] = []

    def remove(operation: Operation, name: str) -> None:
        operations.append(operation)
        present.discard(name)

    def restorable(name: str) -> bool:
        return name.endswith(BACKUP_SUFFIX) or f"{name}{BACKUP_SUFFIX}" in present

    patch_files = {
        *bundle.INJECTOR_FILENAMES,
        *bundle.SUPPORT_FILES,
        *bundle.VARIANT_EXTRA_FILENAMES,
        bundle.FSR4_UPSCALER_FILENAME,
    }
    for name in sorted(patch_files):
        if name in present:
            remove(DeleteFile(name), name)
    for name in bundle.LEGACY_FILES:
        if name in present and not restorable(name):
            remove(RemoveFileOrTree(name), name)
    if PLUGINS_DIR in present:
        ours = {name for name in plugin_entries if f"{PLUGINS_DIR}/{name}" in PLUGIN_FILES}
        if ours == set(plugin_entries):
            remove(RemoveTree(PLUGINS_DIR), PLUGINS_DIR)
        else:
            operations.extend(DeleteFile(f"{PLUGINS_DIR}/{name}") for name in sorted(ours))
    if D3D12_DIR in present:
        remove(RemoveTree(D3D12_DIR), D3D12_DIR)
    for name in dict.fromkeys([*bundle.RESTORABLE_BACKUP_FILES, *bundle.LEGACY_FILES]):
        backup = name + BACKUP_SUFFIX
        if name.endswith(BACKUP_SUFFIX) or backup not in present:
            continue
        if name in present:
            operations.append(DeleteFile(name))
        operations.append(Move(backup, name))
        present.discard(backup)
        present.add(name)
    for name in (UNINSTALLER_FILENAME, bundle.MARKER_FILENAME):
        if name in present:
            remove(DeleteFile(name), name)
    return tuple(operations)
