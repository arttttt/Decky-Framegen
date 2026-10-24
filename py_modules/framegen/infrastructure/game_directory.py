"""Reading game directories and the files a patch copies, and carrying out patch plans."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path

from framegen.domain import patch_record
from framegen.domain import patch_plan as plan
from framegen.infrastructure import files

log = logging.getLogger(__name__)


def bundle_hashes(source: Path, operations: tuple[plan.Operation, ...]) -> dict[str, str]:
    """The identity of every file a plan places, by its path in `source`: a copy's sha256, a link's target."""
    hashes: dict[str, str] = {}
    for operation in operations:
        match operation:
            case plan.Copy(origin, _):
                hashes[origin] = files.sha256(source / origin)
            case plan.Link(origin, _):
                # An absolute origin (the FSR 4 driver DLL in the game's prefix) wins the join: it is its own target.
                hashes[origin] = _link_identity(str((source / origin).absolute()))
    return hashes


def _link_identity(target: str) -> str:
    return f"{patch_record.LINK_PREFIX}{target}"


def current_state(directory: Path, patch: patch_record.PatchRecord) -> dict[str, str | None]:
    """The identity now of every file a recorded patch placed or backed up that is still there: a symlink's
    target (even a dangling one), a file's sha256."""
    paths = [item.path for item in patch.placed] + [backup.backup for backup in patch.backups]
    state: dict[str, str | None] = {}
    for path in paths:
        full = directory / path
        if full.is_symlink():
            state[path] = _link_identity(os.readlink(full))
        elif full.is_file():
            state[path] = files.sha256(full)
    return state


def listing(directory: Path) -> tuple[frozenset[str], frozenset[str]]:
    """The names in a game directory and in its plugins/ subdirectory (empty when there is none)."""
    entries = frozenset(entry.name for entry in directory.iterdir())
    plugins = directory / plan.PLUGINS_DIR
    plugin_entries = frozenset(entry.name for entry in plugins.iterdir()) if plugins.is_dir() else frozenset()
    return entries, plugin_entries


def execute(operations: tuple, directory: Path, copy_root: Path) -> None:
    """Carry out a plan in order, copying from `copy_root`. Filesystem errors propagate; INI edit failures are only logged."""
    for operation in operations:
        match operation:
            case plan.Move(source, destination):
                shutil.move(directory / source, directory / destination)
                log.info(f"Moved {source} → {destination} in {directory}")
            case plan.DeleteFile(name):
                (directory / name).unlink()
                log.info(f"Removed {name} from {directory}")
            case plan.RemoveTree(name):
                shutil.rmtree(directory / name, ignore_errors=True)
                log.info(f"Removed directory {name} from {directory}")
            case plan.RemoveFileOrTree(name):
                path = directory / name
                if path.is_dir() and not path.is_symlink():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    path.unlink()
                log.info(f"Removed legacy {name} from {directory}")
            case plan.Copy(origin, destination):
                (directory / destination).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(copy_root / origin, directory / destination)
                log.info(f"Copied {origin} → {destination} in {directory}")
            case plan.Link(origin, destination):
                # As in bundle_hashes, an absolute origin points the link outside the library.
                (directory / destination).parent.mkdir(parents=True, exist_ok=True)
                os.symlink((copy_root / origin).absolute(), directory / destination)
                log.info(f"Linked {destination} → {copy_root / origin} in {directory}")
            case patch_record.RemoveDirIfEmpty(name):
                path = directory / name
                if path.is_dir() and not any(path.iterdir()):
                    path.rmdir()
                    log.info(f"Removed empty directory {name} from {directory}")


def edit_ini(ini_file: Path, transform, action: str) -> bool:
    """Apply a pure INI transform to a file; failures are logged, never raised."""
    if not ini_file.exists():
        log.warning(f"OptiScaler.ini not found at {ini_file}")
        return False
    try:
        if files.rewrite_text(ini_file, transform):
            log.info(f"OptiScaler.ini: {action} ({ini_file})")
        return True
    except Exception as exc:
        log.error(f"Failed to {action} in {ini_file}: {exc}")
        return False
