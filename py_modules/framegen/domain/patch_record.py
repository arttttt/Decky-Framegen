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
    Copy,
    DeleteFile,
    Link,
    Move,
    Operation,
)

LINK_PREFIX = "link:"
"""What identifies a placed symlink in place of a sha256: `link:` and the path it points to. A link is
ours while it points where we pointed it, whether or not its target still exists."""

FORMAT = 2
"""Markers without this format come from plugin versions before the record existed."""


@dataclass(frozen=True)
class Placed:
    path: str
    sha256: str | None
    """The content placed (a link's is its target, see LINK_PREFIX); None for a file OptiScaler itself rewrites
    (its ini), which is ours whatever it holds."""


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
    operations: tuple[Operation, ...],
    entries: frozenset[str],
    bundle_hashes: dict[str, str],
    carried_over: frozenset[str] = frozenset(),
) -> PatchRecord:
    """The record of a patch plan, made before it runs.

    `entries` is the game directory before the patch; `bundle_hashes` maps every bundle file the
    plan copies to its sha256. `carried_over` names files a
    previous patch placed that this one keeps as they are (the user's OptiScaler.ini settings).
    """
    placed: dict[str, Placed] = {path: Placed(path, None) for path in sorted(carried_over)}
    backups: list[Backup] = []
    for operation in operations:
        match operation:
            case Move(source, destination) if destination == source + BACKUP_SUFFIX:
                backups.append(Backup(source, destination))
            case Copy(source, destination) | Link(source, destination):
                sha = None if destination == INI_FILENAME else bundle_hashes[source]
                placed[destination] = Placed(destination, sha)
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


OK = "ok"
INCOMPLETE = "incomplete"
OLDER_PLUGIN = "older-plugin"


def state(marker: dict) -> str:
    """What a marker says of its patch: OK; INCOMPLETE when the patch stopped before its last file (its
    record still undoes what landed); OLDER_PLUGIN when an earlier plugin version wrote it (undone by a
    reset)."""
    if parse(marker) is None:
        return OLDER_PLUGIN
    return OK if marker.get("complete", True) else INCOMPLETE


def placed_by(patch: PatchRecord | None, path: str) -> bool:
    """Whether a recorded patch placed `path` (a file the directory had before is someone else's)."""
    return patch is not None and any(item.path == path for item in patch.placed)


def intact(patch: PatchRecord, current: dict[str, str | None]) -> bool:
    """Whether everything the patch placed is still there as it placed it (OptiScaler.ini, which
    OptiScaler rewrites, only has to be there)."""
    return all(
        item.path in current and (item.sha256 is None or current[item.path] == item.sha256) for item in patch.placed
    )


def plan_unpatch(
    patch: PatchRecord, current: dict[str, str | None], keep: frozenset[str] = frozenset()
) -> tuple[Operation | RemoveDirIfEmpty, ...]:
    """Undo a recorded patch. `current` maps every placed path and backup still present to its sha256 now.

    A placed file someone replaced since stays when nothing was backed up for it. When something was,
    the backup comes back over it: Unpatch returns the directory to how it was before the patch, and
    a file put over a patched one after patching is its owner's to keep track of.
    `keep` names placed files to leave where they are, for a repatch that carries them over.
    """
    operations: list[Operation | RemoveDirIfEmpty] = []
    backed_up = {backup.original for backup in patch.backups if backup.backup in current}
    for item in patch.placed:
        if item.path not in current or item.path in keep:
            continue
        replaced = item.sha256 is not None and current[item.path] != item.sha256
        if replaced and item.path not in backed_up:
            continue
        operations.append(DeleteFile(item.path))
    for backup in patch.backups:
        if backup.backup in current:
            operations.append(Move(backup.backup, backup.original))
    operations += [RemoveDirIfEmpty(path) for path in patch.created_dirs]
    operations.append(DeleteFile(bundle.MARKER_FILENAME))
    return tuple(operations)
