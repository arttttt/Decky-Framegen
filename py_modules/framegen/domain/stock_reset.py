"""Returning a game that an earlier plugin version patched to how it shipped.

A reset only ever runs for one game the user picked and confirmed. It acts only
on evidence that the plugin was there — its marker, its `.b` backups, or files
only the oldest versions left behind — and says beforehand what it will remove,
what it will restore, and what it removes that the game may have shipped itself.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import bundle, launch_options, marker
from .patch_plan import (
    BACKUP_SUFFIX,
    UNINSTALLER_FILENAME,
    DeleteFile,
    Move,
    Operation,
    RemoveFileOrTree,
    RemoveTree,
    plan_unpatch,
)

MARKER = "marker"
BACKUPS = "backups"
LEFTOVERS = "leftovers"

LEFTOVER_SIGNATURES = frozenset(
    {UNINSTALLER_FILENAME, "dlss-enabler.dll", "nvngx-wrapper.dll", "dlssg_to_fsr3_amd_is_better-3.0.dll"}
)
"""Files only the plugin's oldest versions put in a game directory (OptiScaler itself never ships them)."""

MAYBE_THE_GAMES = frozenset({*bundle.ORIGINAL_DLL_BACKUPS, "nvapi64.dll"})
"""Files a game may ship itself: removed without a backup, only Steam's integrity check brings them back."""


@dataclass(frozen=True)
class ResetPlan:
    evidence: str | None
    """Why the directory counts as patched by the plugin; None means there is nothing to reset."""
    operations: tuple[Operation, ...]
    removed: tuple[str, ...]
    restored: tuple[str, ...]
    unrecoverable: tuple[str, ...]
    """Removed files the game may have shipped and that have no backup."""


def evidence(entries: frozenset[str], marked_elsewhere: bool = False) -> str | None:
    """The strongest sign that the plugin patched a directory, if any.

    `marked_elsewhere`: the game's marker names this directory but sits in another one
    (the game's executable directory changed between patches).
    """
    if marked_elsewhere or bundle.MARKER_FILENAME in entries:
        return MARKER
    backups = {f"{name}{BACKUP_SUFFIX}" for name in [*bundle.RESTORABLE_BACKUP_FILES, *bundle.LEGACY_FILES]}
    if entries & backups:
        return BACKUPS
    if entries & LEFTOVER_SIGNATURES:
        return LEFTOVERS
    return None


def plan(entries: frozenset[str], plugin_entries: frozenset[str], marked_elsewhere: bool = False) -> ResetPlan:
    """What resetting a directory does; nothing at all without evidence of the plugin."""
    found = evidence(entries, marked_elsewhere)
    if found is None:
        return ResetPlan(None, (), (), (), ())
    operations = plan_unpatch(entries, plugin_entries)
    restored = tuple(op.destination for op in operations if isinstance(op, Move))
    removed = tuple(
        op.name
        for op in operations
        if isinstance(op, (DeleteFile, RemoveTree, RemoveFileOrTree)) and op.name not in restored
    )
    unrecoverable = tuple(name for name in removed if name in MAYBE_THE_GAMES)
    return ResetPlan(found, operations, removed, restored, unrecoverable)


def launch_options_after_reset(current: str, stored_original: str) -> str | None:
    """The game's launch options after a reset, or None to leave them as they are.

    Options the plugin wrote give way to the user's own (from the marker when it has them);
    options the user has since changed are not the plugin's to touch.
    """
    if not launch_options.is_managed(current):
        return None
    return marker.original_launch_options(current, stored_original)
