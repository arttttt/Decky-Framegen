"""The OptiScaler library on disk: ~/fgmod/library/{versions,.partial,settings.json}."""

from __future__ import annotations

import shutil
from pathlib import Path

from framegen.domain import library
from framegen.infrastructure.files import read_json, write_json


class LibraryStore:
    def __init__(self, root: Path):
        self.root = root
        self.versions_dir = root / "versions"
        self.partial_dir = root / ".partial"
        self.settings_path = root / "settings.json"

    def installed(self) -> list[library.Installed]:
        """Every version on disk with a readable entry.json; nothing else counts as installed."""
        if not self.versions_dir.is_dir():
            return []
        found = []
        for entry_path in sorted(self.versions_dir.glob(f"*/{library.ENTRY_FILENAME}")):
            parsed = library.parse_entry(read_json(entry_path))
            if parsed is not None and parsed.id == entry_path.parent.name:
                found.append(parsed)
        return found

    def version_dir(self, version_id: str) -> Path:
        return self.versions_dir / version_id

    def size(self, version_id: str) -> int:
        return sum(path.stat().st_size for path in self.version_dir(version_id).rglob("*") if path.is_file())

    def free_bytes(self) -> int:
        self.root.mkdir(parents=True, exist_ok=True)
        return shutil.disk_usage(self.root).free

    # ── staging an install ───────────────────────────────────────────────────

    def clear_partial(self) -> None:
        """Remove what an interrupted install left behind."""
        shutil.rmtree(self.partial_dir, ignore_errors=True)

    def staging(self, version_id: str) -> Path:
        """An empty directory, on the library's filesystem, to assemble a version in."""
        stage = self.partial_dir / version_id
        shutil.rmtree(stage, ignore_errors=True)
        stage.mkdir(parents=True)
        return stage

    @staticmethod
    def files_in(directory: Path) -> frozenset[str]:
        """Every file under `directory`, as paths relative to it with '/'."""
        return frozenset(path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file())

    def commit(self, stage: Path, installed: library.Installed) -> None:
        """Write the entry inside the staged version, then move it into the library in one rename."""
        write_json(stage / library.ENTRY_FILENAME, library.entry_json(installed))
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        stage.replace(self.version_dir(installed.id))

    def replace(self, stage: Path, installed: library.Installed) -> None:
        """Commit a fresh copy of a version that is already in the library. The old copy is moved
        aside first and comes back if the new one can't be moved in."""
        current = self.version_dir(installed.id)
        aside = self.partial_dir / f"{installed.id}.old"
        current.replace(aside)
        try:
            self.commit(stage, installed)
        except OSError:
            aside.replace(current)
            raise
        shutil.rmtree(aside, ignore_errors=True)

    def remove(self, version_id: str) -> None:
        shutil.rmtree(self.version_dir(version_id))

    # ── settings ─────────────────────────────────────────────────────────────

    def default_version(self) -> str | None:
        value = read_json(self.settings_path).get("default_version")
        return str(value) if value else None

    def set_default_version(self, version_id: str | None) -> None:
        settings = read_json(self.settings_path)
        settings["default_version"] = version_id
        self.root.mkdir(parents=True, exist_ok=True)
        staged = self.settings_path.with_name(self.settings_path.name + ".new")
        write_json(staged, settings)
        staged.replace(self.settings_path)

