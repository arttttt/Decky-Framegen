"""Operations on a game directory, and the rules every patch plan shares.

Plans are pure: they read facts about the directory and return operations; a service executes
them. Names are relative to the game directory; copy sources are relative to the files a version
of OptiScaler provides. `plan_unpatch` keeps what earlier plugin versions placed, for resetting
games they patched to stock.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import bundle

BACKUP_SUFFIX = ".b"
INI_FILENAME = "OptiScaler.ini"
PLUGINS_DIR = "plugins"
D3D12_DIR = "D3D12_Optiscaler"
UNINSTALLER_FILENAME = "fgmod-uninstaller.sh"
PLUGIN_FILES = frozenset({bundle.OPTIPATCHER_TARGET})
"""Files a patch has ever placed in the game's plugins/ directory."""


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
class Copy:
    source: str
    destination: str


@dataclass(frozen=True)
class EditIni:
    action: str
    transform: Callable[[str], str]


Operation = Move | DeleteFile | RemoveTree | RemoveFileOrTree | Copy | EditIni


class PlanError(Exception):
    """A plan cannot be made; the message is shown to the user."""


def preserving_existing(operations: tuple[Operation, ...], entries: frozenset[str]) -> tuple[Operation, ...]:
    """The plan with every file that was in the directory kept as a backup before it is removed or overwritten.

    A repatch undoes the previous patch first, so whatever is in the directory now is not the
    patch's. The backup tables above name the usual cases; this makes it hold for every file.
    A file that already has a backup beside it keeps the old behaviour (the backup is the original),
    and a backup itself is never deleted.
    """
    present = set(entries)
    kept: list[Operation] = []
    for operation in operations:
        match operation:
            case Move(source, destination):
                present.discard(source)
                present.add(destination)
            case DeleteFile(name) if name.endswith(BACKUP_SUFFIX):
                continue  # a backup holds someone's original; it is never deleted
            case DeleteFile(name) if name in present and f"{name}{BACKUP_SUFFIX}" not in present:
                kept.append(Move(name, f"{name}{BACKUP_SUFFIX}"))
                present.discard(name)
                present.add(f"{name}{BACKUP_SUFFIX}")
                continue
            case DeleteFile(name):
                present.discard(name)
            case Copy(_, destination) if destination in present and f"{destination}{BACKUP_SUFFIX}" not in present:
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
