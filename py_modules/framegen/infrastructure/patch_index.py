"""~/fgmod/patched.json: the directories the plugin has patched, and what to call each.

It lets the library say which games use a version without searching every game's files.
Each directory's marker stays the truth about its patch; the index only says where to look.
"""

from __future__ import annotations

from pathlib import Path

from framegen.infrastructure.files import read_json, write_json


class PatchIndex:
    def __init__(self, path: Path):
        self.path = path

    def directories(self) -> dict[str, str]:
        """Patched directory → the name to show for it."""
        return {str(directory): str(name) for directory, name in read_json(self.path).items()}

    def add(self, directory: Path, name: str) -> None:
        self._write({**self.directories(), str(directory): name})

    def remove(self, directory: Path) -> None:
        index = self.directories()
        if index.pop(str(directory), None) is not None:
            self._write(index)

    def _write(self, index: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        staged = self.path.with_name(self.path.name + ".new")
        write_json(staged, index)
        staged.replace(self.path)
