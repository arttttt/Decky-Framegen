"""Reading a game directory and the installed bundle for the patch planner, and carrying out its plans."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from framegen.domain import bundle
from framegen.domain import patch_plan as plan
from framegen.infrastructure import files

log = logging.getLogger(__name__)


def bundle_files(fgmod_path: Path) -> frozenset[str]:
    """Every file and directory in the installed bundle, as paths relative to it."""
    if not fgmod_path.exists():
        return frozenset()
    return frozenset(path.relative_to(fgmod_path).as_posix() for path in fgmod_path.rglob("*"))


def read(directory: Path, fgmod_path: Path, previous_variant: str = "") -> plan.GameDirectory:
    """The facts the planner needs: what is there, and which files are the plugin's own copies."""
    entries = frozenset(entry.name for entry in directory.iterdir())
    proxies = frozenset(
        name
        for name in bundle.PROXY_DLL_BACKUPS
        if name in entries and files.files_match(directory / name, fgmod_path / "renames" / name)
    )
    managed = frozenset(
        name
        for name in bundle.ORIGINAL_DLL_BACKUPS
        if name in entries
        and any(
            files.files_match(directory / name, fgmod_path / candidate)
            for candidate in plan.managed_support_candidates(name)
        )
    )
    return plan.GameDirectory(entries, proxies, managed, previous_variant)


def execute(operations: tuple[plan.Operation, ...], directory: Path, fgmod_path: Path) -> None:
    """Carry out a plan in order. Filesystem errors propagate; INI edit failures are only logged."""
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
            case plan.CopyFromBundle(source, destination):
                shutil.copy2(fgmod_path / source, directory / destination)
                log.info(f"Copied {source} → {destination} in {directory}")
            case plan.MergeTreeFromBundle(name):
                shutil.copytree(fgmod_path / name, directory / name, dirs_exist_ok=True)
                log.info(f"Synced {name}/ into {directory}")
            case plan.EditIni(action, transform):
                edit_ini(directory / plan.INI_FILENAME, transform, action)


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
