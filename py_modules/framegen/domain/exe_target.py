"""Choosing which executable — and so which directory — of a game to patch.

A game install can hold launchers, crash reporters, redistributables and the
real game binary. A running executable wins; otherwise each candidate is
scored by path and name heuristics.
"""

from __future__ import annotations

import re
from pathlib import Path

# Path fragments of executables that are not the game itself.
_NOT_THE_GAME = (
    "crashreport",
    "crashreportclient",
    "eac",
    "easyanticheat",
    "beclient",
    "eosbootstrap",
    "benchmark",
    "uninstall",
    "setup",
    "launcher",
    "updater",
    "bootstrap",
    "_redist",
    "prereq",
)


def normalized_path(value: str) -> str:
    """Lower-case, forward slashes, Wine's Z: drive mapped back to /: comparable across Wine and Linux paths."""
    normalized = value.lower().replace("\\", "/")
    normalized = normalized.replace("z:/", "/")
    return normalized.replace("//", "/")


def _alnum(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def score(exe: Path, install_root: Path, game_name: str) -> int:
    """How likely `exe` is the game's main binary; higher is better."""
    normalized = normalized_path(str(exe))
    name = exe.name.lower()
    total = 0
    if normalized.endswith("-win64-shipping.exe"):
        total += 300
    if "shipping.exe" in name:
        total += 220
    if "/binaries/win64/" in normalized:
        total += 200
    if "/win64/" in normalized:
        total += 80
    if exe.parent == install_root:
        total += 20
    game, stem, root = _alnum(game_name), _alnum(exe.stem), _alnum(install_root.name)
    if game and game in stem:
        total += 120
    if root and root in stem:
        total += 90
    total -= 200 * sum(1 for fragment in _NOT_THE_GAME if fragment in normalized)
    return total - len(exe.parts)


def running_executable(candidates: list[Path], process_command_lines: list[str]) -> Path | None:
    """The candidate that appears in a running process's command line; the longest path wins."""
    normalized_candidates = [(exe, normalized_path(str(exe))) for exe in candidates]
    matches: list[tuple[int, Path]] = []
    for line in process_command_lines:
        normalized_line = normalized_path(line)
        for exe, normalized_exe in normalized_candidates:
            if normalized_exe in normalized_line:
                matches.append((len(normalized_exe), exe))
    if not matches:
        return None
    matches.sort(key=lambda item: item[0], reverse=True)
    return matches[0][1]


def patch_target(
    install_root: Path, game_name: str, candidates: list[Path], running: Path | None
) -> tuple[Path, Path | None]:
    """The directory to patch and the executable it was chosen for (None when the game has no .exe)."""
    if not candidates:
        return install_root, None
    if running:
        return running.parent, running
    best = max(candidates, key=lambda exe: score(exe, install_root, game_name))
    return best.parent, best
