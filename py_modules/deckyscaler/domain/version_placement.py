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

from . import fsr4
from .bundle import VALID_DLL_NAMES
from .library import Family
from .patch_plan import BACKUP_SUFFIX, INI_FILENAME, Copy, Link, Move, Operation, PlanError, preserving_existing

INJECTOR = "OptiScaler.dll"


@dataclass(frozen=True)
class Request:
    dll_name: str
    reset_ini: bool = False
    """Replace the game's OptiScaler.ini with the version's instead of keeping it."""
    fsr4_driver: str | None = None
    """Where the game's Proton puts AMD's FSR 4 driver DLL (an absolute path; it may not be there yet).
    OptiScaler loads that DLL only from its own directory, never by name, so a patch links it there."""


def is_for_the_game(path: str) -> bool:
    """Whether an archive file belongs in the game directory (not licenses, notes or setup scripts)."""
    parts = PurePosixPath(path).parts
    name = parts[-1]
    if parts[0] == "Licenses" or name.endswith(".bat") or name.startswith("setup_"):
        return False
    return not (len(parts) == 1 and name.endswith(".txt"))


def plan_patch(entries: frozenset[str], files: frozenset[str], family: Family, request: Request) -> tuple[Operation, ...]:
    """The operations that patch a directory holding `entries` with a version whose archive holds `files`.

    The version's files are symlinks into the library, so a game holds no copy of OptiScaler. Only
    OptiScaler.ini is copied: OptiScaler writes the user's settings to it, which stay the game's own."""
    if request.dll_name not in VALID_DLL_NAMES:
        raise PlanError(f"Invalid proxy DLL name: {request.dll_name}")
    missing = family.required - files
    if missing:
        raise PlanError(f"The OptiScaler version lacks {', '.join(sorted(missing))}. Install it again.")

    operations: list[Operation] = []
    # Another proxy left in the directory would load OptiScaler a second time.
    for name in sorted(VALID_DLL_NAMES):
        if name in entries and name + BACKUP_SUFFIX not in entries:
            operations.append(Move(name, name + BACKUP_SUFFIX))
    operations.append(Link(INJECTOR, request.dll_name))

    fresh_ini = request.reset_ini or INI_FILENAME not in entries
    if fresh_ini:
        # The user's settings go into it after placing (Patcher, domain settings_layers).
        operations.append(Copy(INI_FILENAME, INI_FILENAME))

    for path in sorted(files):
        if path not in (INJECTOR, INI_FILENAME) and is_for_the_game(path):
            operations.append(Link(path, path))

    driver = driver_path(family)
    # A DLL already there is the user's own choice of FSR 4: it stays, and nothing is linked over it.
    if request.fsr4_driver and driver not in entries:
        operations.append(Link(request.fsr4_driver, driver))
    return preserving_existing(tuple(operations), entries)


def driver_path(family: Family) -> str:
    """Where in the game's directory OptiScaler looks for AMD's FSR 4 driver DLL."""
    return str(PurePosixPath(family.main_dir) / fsr4.DLL)
