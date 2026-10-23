"""What a patch did to a game directory, recorded in its marker before the first file lands.

Unpatching undoes exactly that record: it removes the files the patch placed, restores the
backups it made and removes the directories it created. It touches nothing else, so it works
for any OptiScaler layout and for versions no longer in the library. A file the game has
replaced since (an update) is the game's: it stays, and the backup it superseded is dropped.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from . import bundle
from .patch_plan import (
    BACKUP_SUFFIX,
    INI_FILENAME,
    CopyFromBundle,
    DeleteFile,
    MergeTreeFromBundle,
    Move,
    Operation,
)

FORMAT = 2
"""Markers without this format come from plugin versions before the record existed."""


@dataclass(frozen=True)
class Placed:
    path: str
    sha256: str | None
    """The content placed; None for a file OptiScaler itself rewrites (its ini), which is ours whatever it holds."""


@dataclass(frozen=True)
class Backup:
    original: str
    backup: str


@dataclass(frozen=True)
class PatchRecord:
    placed: tuple[Placed, ...]
    backups: tuple[Backup, ...]
    created_dirs: tuple[str, ...]


@dataclass(frozen=True)
class RemoveDirIfEmpty:
    name: str


def record(
    operations: tuple[Operation, ...], entries: frozenset[str], bundle_hashes: dict[str, str]
) -> PatchRecord:
    """The record of a patch plan, made before it runs.

    `entries` is the game directory before the patch; `bundle_hashes` maps every bundle file the
    plan copies (directories expanded to their files) to its sha256.
    """
    placed: dict[str, Placed] = {}
    backups: list[Backup] = []
    for operation in operations:
        match operation:
            case Move(source, destination) if destination == source + BACKUP_SUFFIX:
                backups.append(Backup(source, destination))
            case CopyFromBundle(source, destination):
                sha = None if destination == INI_FILENAME else bundle_hashes[source]
                placed[destination] = Placed(destination, sha)
            case MergeTreeFromBundle(name):
                for path, sha in sorted(bundle_hashes.items()):
                    if path.startswith(f"{name}/"):
                        placed[path] = Placed(path, sha)
    created = sorted(
        {
            str(parent)
            for item in placed
            for parent in PurePosixPath(item).parents
            if str(parent) != "." and str(parent).split("/")[0] not in entries
        },
        key=lambda path: (-path.count("/"), path),
    )
    return PatchRecord(tuple(placed.values()), tuple(backups), tuple(created))


def to_json(patch: PatchRecord, complete: bool) -> dict:
    return {
        "format": FORMAT,
        "complete": complete,
        "placed": [{"path": p.path, "sha256": p.sha256} for p in patch.placed],
        "backups": [{"original": b.original, "backup": b.backup} for b in patch.backups],
        "created_dirs": list(patch.created_dirs),
    }


def parse(marker: dict) -> PatchRecord | None:
    """The record in a marker; None for a marker an earlier plugin version wrote."""
    if marker.get("format") != FORMAT:
        return None
    try:
        return PatchRecord(
            tuple(Placed(str(p["path"]), None if p["sha256"] is None else str(p["sha256"])) for p in marker["placed"]),
            tuple(Backup(str(b["original"]), str(b["backup"])) for b in marker["backups"]),
            tuple(str(d) for d in marker["created_dirs"]),
        )
    except (KeyError, TypeError):
        return None


def plan_unpatch(patch: PatchRecord, current: dict[str, str | None]) -> tuple[Operation | RemoveDirIfEmpty, ...]:
    """Undo a recorded patch. `current` maps every placed path and backup still present to its sha256 now."""
    operations: list[Operation | RemoveDirIfEmpty] = []
    replaced_by_game: set[str] = set()
    for item in patch.placed:
        if item.path not in current:
            continue
        if item.sha256 is not None and current[item.path] != item.sha256:
            replaced_by_game.add(item.path)
            continue
        operations.append(DeleteFile(item.path))
    for backup in patch.backups:
        if backup.backup not in current:
            continue
        if backup.original in replaced_by_game:
            # The game shipped a newer file since; its old copy must not come back over it.
            operations.append(DeleteFile(backup.backup))
        else:
            operations.append(Move(backup.backup, backup.original))
    operations += [RemoveDirIfEmpty(path) for path in patch.created_dirs]
    operations.append(DeleteFile(bundle.MARKER_FILENAME))
    return tuple(operations)
