"""How a library version of OptiScaler is laid into a game directory.

The version's archive is laid out as the game needs it, so the plan mirrors it: OptiScaler.dll
goes in under the chosen proxy DLL's name, OptiScaler.ini is placed (or the game's kept), and
every other file goes to the same relative path — except what is only for people reading the
archive (licenses, notes, Windows/Linux setup scripts). Every file in the directory that the plan
would remove or overwrite is backed up first, and only one proxy DLL may load OptiScaler.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath

from . import ini
from .bundle import VALID_DLL_NAMES
from .library import Family
from .patch_plan import BACKUP_SUFFIX, INI_FILENAME, Copy, EditIni, Move, Operation, PlanError, preserving_existing

INJECTOR = "OptiScaler.dll"


@dataclass(frozen=True)
class Request:
    dll_name: str
    variant: str
    reset_ini: bool = False
    """Replace the game's OptiScaler.ini with the version's instead of keeping it."""


def is_for_the_game(path: str) -> bool:
    """Whether an archive file belongs in the game directory (not licenses, notes or setup scripts)."""
    parts = PurePosixPath(path).parts
    name = parts[-1]
    if parts[0] == "Licenses" or name.endswith(".bat") or name.startswith("setup_"):
        return False
    return not (len(parts) == 1 and name.endswith(".txt"))


def plan_patch(entries: frozenset[str], files: frozenset[str], family: Family, request: Request) -> tuple[Operation, ...]:
    """The operations that patch a directory holding `entries` with a version whose archive holds `files`."""
    if request.dll_name not in VALID_DLL_NAMES:
        raise PlanError(f"Invalid proxy DLL name: {request.dll_name}")
    if request.variant not in family.variants:
        raise PlanError(f"OptiScaler {family.id} has no FSR 4 variant {request.variant}")
    missing = family.required - files
    if missing:
        raise PlanError(f"The OptiScaler version lacks {', '.join(sorted(missing))}. Install it again.")

    operations: list[Operation] = []
    # Another proxy left in the directory would load OptiScaler a second time.
    for name in sorted(VALID_DLL_NAMES):
        if name in entries and name + BACKUP_SUFFIX not in entries:
            operations.append(Move(name, name + BACKUP_SUFFIX))
    operations.append(Copy(INJECTOR, request.dll_name))

    fresh_ini = request.reset_ini or INI_FILENAME not in entries
    if fresh_ini:
        operations.append(Copy(INI_FILENAME, INI_FILENAME))
        operations.append(EditIni("apply the plugin's defaults", lambda text: ini.apply_overrides(text, family.ini_defaults)))
    others = family.other_variant_keys(request.variant)
    chosen = family.variants[request.variant].ini
    operations.append(
        EditIni(
            f"apply FSR 4 variant {request.variant}",
            lambda text: ini.apply_overrides(ini.reset_to_auto(text, others), chosen),
        )
    )

    for path in sorted(files):
        if path not in (INJECTOR, INI_FILENAME) and is_for_the_game(path):
            operations.append(Copy(path, path))
    return preserving_existing(tuple(operations), entries)
