"""The user's OptiScaler settings: what each page shows, and changing them, global or a game's own."""

from __future__ import annotations

import logging
from pathlib import Path

from framegen.application.patcher import NO_VERSION, Patcher
from framegen.domain import bundle, exe_target, ini_schema, library, patch_record, settings_layers
from framegen.domain import patch_plan as plan
from framegen.domain.settings_layers import Key, Layer
from framegen.infrastructure import files, processes
from framegen.infrastructure import steam as steam_library

log = logging.getLogger(__name__)

GLOBAL_SCOPE = "global"
GAME_RUNNING = "Close the game first: OptiScaler reads its settings when the game starts, and saving in its menu would overwrite them."


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


class Settings:
    def __init__(self, home: Path):
        self.patcher = Patcher(home)
        self.home = home
        self.library = self.patcher.library
        self.store = self.patcher.settings

    # ── schemas ──────────────────────────────────────────────────────────────

    def _schema(self, version_id: str | None) -> tuple[str, tuple[ini_schema.Section, ...]] | None:
        """The settings of a version: the one named while it is downloaded, else the newest."""
        installed = self.library.installed()
        entry = library.version_to_patch_with(installed, version_id)
        if entry is None:
            return None
        source = self.library.version_dir(entry.id) / library.FILES_DIRNAME / plan.INI_FILENAME
        return entry.id, ini_schema.parse(files.read_text(source))

    def _game(self, appid: str) -> tuple[Path | None, dict]:
        """A Steam game's patched directory (None when it isn't patched) and its marker."""
        game = steam_library.find_game(self.home, appid)
        marker_path = self.patcher.find_marker(game.install_path) if game else None
        return (marker_path.parent, files.read_json(marker_path)) if marker_path else (None, {})

    # ── what the pages show ──────────────────────────────────────────────────

    def global_settings(self) -> dict:
        """Global settings against the newest downloaded version's settings."""
        schema = self._schema(None)
        if schema is None:
            return _error(NO_VERSION)
        version_id, sections = schema
        global_layer = self.store.global_layer()
        resolved = settings_layers.resolve(sections, global_layer, {})
        return {
            "status": "success",
            "version": version_id,
            "sections": settings_layers.view_json(sections, resolved),
            "unsupported": [f"{s}.{k}" for s, k in settings_layers.unsupported(sections, global_layer)],
        }

    def game_settings(self, appid: str) -> dict:
        """A game's settings against its version's (the newest when it isn't patched), each with its source."""
        directory, details = self._game(appid)
        schema = self._schema(details.get("optiscaler_version"))
        if schema is None:
            return _error(NO_VERSION)
        version_id, sections = schema
        game_layer = self.store.game_layer(appid)
        resolved = settings_layers.resolve(sections, self.store.global_layer(), game_layer)
        return {
            "status": "success",
            "version": version_id,
            "patched": directory is not None,
            "running": directory is not None and self._running(directory),
            "sections": settings_layers.view_json(sections, resolved),
            "unsupported": [f"{s}.{k}" for s, k in settings_layers.unsupported(sections, game_layer)],
        }

    # ── changing them ────────────────────────────────────────────────────────

    def set_setting(self, scope: str, section: str, key: str, value: str | None) -> dict:
        """Set a global or a game's value (None clears it), then write the settings into the games they
        reach: every patched game for a global one, the game for its own. A running game is refused, or
        for a global change skipped and named."""
        target: Key = (section, key)
        if scope == GLOBAL_SCOPE:
            schema = self._schema(None)
            if schema is None:
                return _error(NO_VERSION)
            if value is not None and not self._accepted(schema[1], target, value):
                return _error(f"{section}.{key} doesn't take {value!r}.")
            self.store.save_global(settings_layers.with_value(self.store.global_layer(), target, value))
            skipped = self._apply_everywhere()
            return {"status": "success", "skipped": skipped}
        directory, details = self._game(scope)
        if directory is not None and self._running(directory):
            return _error(GAME_RUNNING)
        schema = self._schema(details.get("optiscaler_version"))
        if schema is None:
            return _error(NO_VERSION)
        if value is not None and not self._accepted(schema[1], target, value):
            return _error(f"{section}.{key} doesn't take {value!r}.")
        self.store.save_game(scope, settings_layers.with_value(self.store.game_layer(scope), target, value))
        if directory is not None:
            self._apply(directory, details, scope)
        return {"status": "success", "skipped": []}

    def reset_game_settings(self, appid: str) -> dict:
        """Drop a game's own settings: it follows the global ones again."""
        directory, details = self._game(appid)
        if directory is not None and self._running(directory):
            return _error(GAME_RUNNING)
        self.store.save_game(appid, {})
        if directory is not None:
            self._apply(directory, details, appid)
        return {"status": "success"}

    def _accepted(self, sections: tuple[ini_schema.Section, ...], target: Key, value: str) -> bool:
        setting = next((s for section in sections for s in section.settings if (s.section, s.key) == target), None)
        return setting is not None and settings_layers.accepts(setting, value)

    def _apply(self, directory: Path, details: dict, appid: str | None) -> None:
        """The settings into one patched directory's ini, if the patch placed it."""
        version_id = details.get("optiscaler_version")
        if not version_id or not patch_record.placed_by(patch_record.parse(details), plan.INI_FILENAME):
            return
        source = self.library.version_dir(version_id) / library.FILES_DIRNAME
        self.patcher.apply_settings(directory, source, appid)

    def _apply_everywhere(self) -> list[str]:
        """The settings into every patched game; the names of the running ones, which are left alone."""
        skipped = []
        for directory, name in self.patcher.patches.directories().items():
            path = Path(directory)
            details = files.read_json(path / bundle.MARKER_FILENAME)
            if not details:
                continue
            if self._running(path):
                skipped.append(name)
                continue
            self._apply(path, details, str(details.get("appid") or "") or None)
        return skipped

    @staticmethod
    def _running(directory: Path) -> bool:
        executables = [exe for exe in directory.glob("*.exe") if exe.is_file()]
        return bool(executables) and exe_target.running_executable(executables, processes.command_lines()) is not None
