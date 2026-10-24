"""Patching and unpatching games: the one owner of the patch lifecycle.

Manual directory patching and Steam AppID patching are two entry points into
the same plan-and-execute path. Results are the plain dicts the frontend reads.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from framegen.domain import bundle, exe_target, fsr4, launch_options, library, marker, patch_record, steam, stock_reset, version_placement
from framegen.domain import patch_plan as plan
from framegen.infrastructure import files, game_directory, processes, proton
from framegen.infrastructure.library_store import LibraryStore
from framegen.infrastructure.patch_index import PatchIndex
from framegen.infrastructure import steam as steam_library

log = logging.getLogger(__name__)

NO_VERSION = "No OptiScaler version is downloaded. Download one under OptiScaler versions first."
BUNDLE_IS_NOT_A_GAME = "The target directory is the OptiScaler bundle itself. Aborting to prevent accidental deletion."
PATCHED_BY_AN_OLDER_VERSION = (
    "This game was patched by an older version of the plugin. Unpatch it first: the plugin shows what that removes."
)
LAUNCH_OPTIONS_UNKNOWN = (
    "Steam didn't say what this game's launch options are, so Unpatch couldn't put them back. "
    "Nothing was changed; try patching again."
)
RECORD = "record"
"""How a directory is unpatched: by its patch record, exactly as the patch recorded it."""
RESET = "reset"
"""How a directory an older plugin version patched is unpatched: by what those versions placed, after the user confirms."""


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


def _fsr4_json(state: fsr4.State | None) -> dict | None:
    return None if state is None else {"state": state.kind, "tool": state.tool, "version": state.version}


class Patcher:
    def __init__(self, home: Path):
        self.home = home
        self.fgmod_path = home / "fgmod"
        self.library = LibraryStore(self.fgmod_path / "library")
        self.patches = PatchIndex(self.fgmod_path / "patched.json")

    # ── directories ──────────────────────────────────────────────────────────

    def resolve_directory(self, directory: str) -> Path:
        """A user-supplied directory, checked to exist and be writable."""
        target = Path(directory).expanduser()
        if not target.exists():
            raise FileNotFoundError(f"Target directory does not exist: {directory}")
        if not target.is_dir():
            raise NotADirectoryError(f"Target path is not a directory: {directory}")
        if not os.access(target, os.W_OK | os.X_OK):
            raise PermissionError(f"Insufficient permissions for {directory}")
        return target

    def patch_directory(
        self,
        directory: Path,
        dll_name: str,
        *,
        version_id: str | None = None,
        reset_ini: bool = False,
        steam_game: marker.SteamGame | None = None,
        fsr4_driver: Path | None = None,
    ) -> dict:
        """Patch a directory with a library version and record it in a marker. A patch that names no
        version (the launch wrapper's, unless FGMOD_VERSION is set) keeps the one the directory is
        patched with, else takes the newest downloaded."""
        if dll_name not in bundle.VALID_DLL_NAMES:
            return _error(f"Invalid proxy DLL name: {dll_name}")
        marker_path = directory / bundle.MARKER_FILENAME
        installed = self.library.installed()
        if version_id:
            entry = next((e for e in installed if e.id == version_id), None)
            if entry is None:
                return _error(f"OptiScaler {version_id} is not in the library.")
        else:
            entry = library.version_to_patch_with(installed, files.read_json(marker_path).get("optiscaler_version"))
            if entry is None:
                return _error(NO_VERSION)
        family = library.FAMILIES[entry.family]
        source = self.library.version_dir(entry.id) / library.FILES_DIRNAME

        carried_over: frozenset[str] = frozenset()
        if marker_path.exists():
            # A repatch first undoes the previous patch, exactly as its marker records it, keeping
            # the OptiScaler.ini it placed (the user's settings) unless asked to reset it or the
            # new version is of another family, whose ini keys differ.
            previous_marker = files.read_json(marker_path)
            previous = patch_record.parse(previous_marker)
            same_family = previous_marker.get("family") == entry.family
            if previous is not None and same_family and not reset_ini and plan.INI_FILENAME in {p.path for p in previous.placed}:
                carried_over = frozenset({plan.INI_FILENAME})
            undone = self.unpatch_directory(directory, keep=carried_over)
            if undone["status"] != "success":
                return undone
        try:
            entries, _ = game_directory.listing(directory)
            driver = version_placement.driver_path(family)
            if os.path.lexists(directory / driver):
                entries |= {driver}
            request = version_placement.Request(dll_name, reset_ini, str(fsr4_driver) if fsr4_driver else None)
            operations = version_placement.plan_patch(
                entries, self.library.files_in(source), family, request
            )
            log.info(f"Patching {directory} with OptiScaler {entry.id}, {dll_name}")
            recorded = patch_record.record(
                operations, entries, game_directory.bundle_hashes(source, operations), carried_over & entries
            )
            details = marker.build(
                dll_name=dll_name,
                target_dir=directory,
                backed_up_files=[backup.original for backup in recorded.backups],
                optiscaler_version=entry.id,
                family=entry.family,
                patched_at=datetime.now(timezone.utc).isoformat(),
                steam_game=steam_game,
            )
            # The record lands before the first file does, so even an interrupted patch can be undone.
            files.write_json(marker_path, {**details, **patch_record.to_json(recorded, complete=False)})
            self._remember(directory, steam_game.name if steam_game else str(directory))
            game_directory.execute(operations, directory, source)
            files.write_json(marker_path, {**details, **patch_record.to_json(recorded, complete=True)})
        except plan.PlanError as exc:
            return _error(str(exc))
        except PermissionError as exc:
            log.error(f"Patch permission error: {exc}")
            return _error(f"Permission error while patching: {exc}")
        except Exception as exc:
            log.error(f"Patch failed: {exc}")
            return _error(f"Patch failed: {exc}")
        return {
            "status": "success",
            "message": f"OptiScaler {entry.version} is in {directory}.",
            "optiscaler_version": entry.id,
        }

    def _is_bundle(self, directory: Path) -> bool:
        """Whether `directory` is ~/fgmod or inside it: never a game, never to be unpatched or reset."""
        return directory.resolve().is_relative_to(self.fgmod_path.resolve())

    def unpatch_directory(self, directory: Path, keep: frozenset[str] = frozenset()) -> dict:
        """Undo the patch recorded in the directory's marker. The marker goes last, so a failure keeps it.

        `keep` names placed files a repatch carries over instead of removing.
        """
        if self._is_bundle(directory):
            return _error(BUNDLE_IS_NOT_A_GAME)
        marker_path = directory / bundle.MARKER_FILENAME
        if not marker_path.exists():
            self._forget(directory)
            return {"status": "success", "message": f"No Framegen patch found in {directory}"}
        recorded = patch_record.parse(files.read_json(marker_path))
        if recorded is None:
            return _error(PATCHED_BY_AN_OLDER_VERSION)
        try:
            operations = patch_record.plan_unpatch(recorded, game_directory.current_state(directory, recorded), keep)
            game_directory.execute(operations, directory, self.fgmod_path)
        except PermissionError as exc:
            log.error(f"Unpatch permission error: {exc}")
            return _error(f"Permission error while unpatching: {exc}")
        except Exception as exc:
            log.error(f"Unpatch failed: {exc}")
            return _error(f"Unpatch failed: {exc}")
        self._forget(directory)
        return {"status": "success", "message": f"OptiScaler files removed from {directory}"}

    # The index of patched directories follows the markers: an entry is added once a marker is
    # written and dropped once it is gone. Failing to update it never fails a patch.

    def _remember(self, directory: Path, name: str) -> None:
        try:
            self.patches.add(directory, name)
        except OSError as exc:
            log.warning(f"Updating the index of patched directories failed: {exc}")

    def _forget(self, directory: Path) -> None:
        try:
            self.patches.remove(directory)
        except OSError as exc:
            log.warning(f"Updating the index of patched directories failed: {exc}")

    def _patched_with(self, version_id: str) -> list[tuple[str, dict]]:
        """The name and marker of every indexed directory whose marker names this library version."""
        markers = [
            (name, files.read_json(Path(directory) / bundle.MARKER_FILENAME))
            for directory, name in self.patches.directories().items()
        ]
        return sorted((name, details) for name, details in markers if details.get("optiscaler_version") == version_id)

    def games_using(self, version_id: str) -> list[str]:
        """The patched games and directories whose marker names this library version."""
        return [name for name, _ in self._patched_with(version_id)]

    def games_linked_to(self, version_id: str) -> list[str]:
        """The games whose files are symlinks into this library version: removing it would break them."""
        return [name for name, details in self._patched_with(version_id) if details.get("placement") == marker.LINK]

    def patch_user_directory(
        self, directory: str, dll_name: str, version_id: str | None = None
    ) -> dict:
        try:
            target = self.resolve_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            log.error(f"Manual patch validation failed: {exc}")
            return _error(str(exc))
        return self.patch_directory(target, dll_name, version_id=version_id)

    def unpatch_user_directory(self, directory: str, confirmed_reset: bool = False) -> dict:
        """Unpatch a directory the user picked: by its record, or — for an older plugin version's
        patch, once the user confirmed what the preview showed — by resetting it."""
        try:
            target = self.resolve_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            log.error(f"Manual unpatch validation failed: {exc}")
            return _error(str(exc))
        if confirmed_reset and self._unpatch_mode(target / bundle.MARKER_FILENAME) == RESET:
            return self._reset_directory(target)
        # An older plugin's marker is refused there: its patch needs the confirmed reset.
        return self.unpatch_directory(target)

    def preview_unpatch_directory(self, directory: str) -> dict:
        try:
            target = self.resolve_directory(directory)
            if self._unpatch_mode(target / bundle.MARKER_FILENAME) == RECORD:
                return {"status": "success", "mode": RECORD, "target_dir": str(target)}
            preview, _ = self._reset_plan(target, None, None)
            return {**preview, "mode": RESET} if preview["status"] == "success" else preview
        except Exception as exc:
            log.error(f"[Framegen] preview_unpatch_directory failed for {directory}: {exc}")
            return _error(str(exc))

    @staticmethod
    def _unpatch_mode(marker_path: Path | None) -> str:
        """RECORD when the marker holds a patch record; RESET for anything else (an older plugin's
        marker, or no marker — then only the reset's own evidence rules decide whether anything is ours)."""
        if marker_path is not None and marker_path.is_file() and patch_record.parse(files.read_json(marker_path)):
            return RECORD
        return RESET

    def path_defaults(self) -> dict:
        """Starting points for the manual directory picker: home, and the games of the first Steam library
        found (native or Flatpak), else where native Steam would keep them."""
        libraries = [library for library in steam_library.library_paths(self.home) if (library / "steamapps").is_dir()]
        steam_root = libraries[0] if libraries else steam.steam_root_candidates(self.home)[0]
        return {"home": str(self.home), "steam_common": str(steam_root / "steamapps" / "common")}

    # ── Steam games ──────────────────────────────────────────────────────────

    def list_games(self) -> dict:
        try:
            games = [
                {"appid": game.appid, "name": game.name, "install_found": game.install_path.exists()}
                for game in steam_library.installed_games(self.home)
            ]
        except Exception as exc:
            log.error(str(exc))
            return _error(str(exc))
        return {"status": "success", "games": games}

    def _running_executable(self, candidates: list[Path]) -> Path | None:
        if not candidates:
            return None
        return exe_target.running_executable(candidates, processes.command_lines())

    def _is_running(self, game: steam_library.InstalledGame) -> bool:
        return self._running_executable(steam_library.executables(game.install_path)) is not None

    def _fsr4(self, game: steam_library.InstalledGame) -> tuple[fsr4.State | None, Path | None]:
        """The game's FSR 4 under Proton, and — when a patch should ask Proton to fetch it — where in the
        game's prefix the DLL lands."""
        amd = proton.amd_gpu()
        tool = proton.compat_tool(self.home, game.appid)
        tool_dir = proton.tool_directory(self.home, tool) if tool else None
        reads_variable = tool_dir is not None and proton.reads_upgrade_variable(tool_dir)
        prefix = proton.compatdata(game.library_path, game.appid)
        state = fsr4.state(amd, tool, reads_variable, proton.dll_in_prefix(prefix), proton.tracked_version(prefix))
        return state, proton.prefix_dll(prefix) if fsr4.wants_upgrade_variable(amd, reads_variable) else None

    def _patch_target(self, game: steam_library.InstalledGame) -> tuple[Path, Path | None]:
        candidates = steam_library.executables(game.install_path)
        running = self._running_executable(candidates)
        return exe_target.patch_target(game.install_path, game.name, candidates, running)

    def _find_marker(self, install_root: Path) -> Path | None:
        """The game's patch marker: where the patch index says the plugin patched it, else by searching
        the whole install (a patch by an older plugin version, or a game the plugin never patched)."""
        if not install_root.exists():
            return None
        for directory in self.patches.directories():
            marker_path = Path(directory) / bundle.MARKER_FILENAME
            if marker_path.parent.is_relative_to(install_root) and marker_path.is_file():
                return marker_path
        try:
            return next((path for path in install_root.rglob(bundle.MARKER_FILENAME) if path.is_file()), None)
        except OSError:
            return None

    def game_status(self, appid: str) -> dict:
        try:
            return self._game_status(appid)
        except Exception as exc:
            log.error(f"[Framegen] get_game_status failed for {appid}: {exc}")
            return _error(str(exc))

    def _game_status(self, appid: str) -> dict:
        game = steam_library.find_game(self.home, str(appid))
        unpatched = {
            "status": "success",
            "appid": str(appid),
            "patched": False,
            "dll_name": None,
            "target_dir": None,
            "newer_version": None,
            "fsr4": None,
        }
        if game is None:
            return {**unpatched, "install_found": False, "message": "Game not found in Steam library."}
        if not game.install_path.exists():
            return {**unpatched, "name": game.name, "install_found": False, "message": "Game install directory not found."}
        # FSR 4 is the Proton's business, so it is told whether the game is patched or not.
        unpatched["fsr4"] = _fsr4_json(self._fsr4(game)[0])
        marker_path = self._find_marker(game.install_path)
        if marker_path is None:
            return {**unpatched, "name": game.name, "install_found": True, "message": "Not patched."}

        metadata = files.read_json(marker_path)
        if patch_record.parse(metadata) is None:
            return {
                **unpatched, "name": game.name, "install_found": True, "patched": True,
                "target_dir": str(marker_path.parent), "message": PATCHED_BY_AN_OLDER_VERSION,
            }
        dll_name = metadata.get("dll_name", bundle.DEFAULT_PROXY_DLL)
        # The marker sits in the directory it patched; the path written into it can go stale.
        target_dir = marker_path.parent
        dll_present = (target_dir / dll_name).exists()
        version = metadata.get("optiscaler_version")
        if dll_present:
            message = f"Patched with OptiScaler {version} using {dll_name}."
        else:
            message = f"Marker found but {dll_name} is missing. Patch it again."
        return {
            "status": "success",
            "appid": str(appid),
            "name": game.name,
            "install_found": True,
            "patched": dll_present,
            "dll_name": dll_name,
            "target_dir": str(target_dir),
            "patched_at": metadata.get("patched_at"),
            "optiscaler_version": version,
            "newer_version": library.newer_in_channel(self.library.installed(), version),
            "fsr4": unpatched["fsr4"],
            "message": message,
        }

    def patch_game(
        self, appid: str, dll_name: str, current_launch_options: str | None, version_id: str | None = None
    ) -> dict:
        """Patch a Steam game. `current_launch_options` is None when Steam didn't say what they are."""
        try:
            return self._patch_game(appid, dll_name, current_launch_options, version_id)
        except Exception as exc:
            log.error(f"[Framegen] patch_game failed for {appid}: {exc}")
            return _error(str(exc))

    def _patch_game(
        self, appid: str, dll_name: str, current_launch_options: str | None, version_id: str | None
    ) -> dict:
        game = steam_library.find_game(self.home, str(appid))
        if game is None:
            return _error("Game not found in Steam library.")
        if not game.install_path.exists():
            return _error("Game install directory does not exist.")
        candidates = steam_library.executables(game.install_path)
        if self._running_executable(candidates) is not None:
            return _error("Close the game before patching.")
        existing_marker = self._find_marker(game.install_path)
        existing = files.read_json(existing_marker) if existing_marker else {}
        stored = str(existing.get("original_launch_options") or "") if existing_marker else None
        original_options = marker.original_launch_options(current_launch_options, stored)
        if original_options is None:
            return _error(LAUNCH_OPTIONS_UNKNOWN)

        target_dir, target_exe = exe_target.patch_target(game.install_path, game.name, candidates, None)
        if existing_marker and existing_marker.parent != target_dir:
            # The game's executable moved since its last patch; that directory is undone first.
            moved = self.unpatch_directory(existing_marker.parent)
            if moved["status"] != "success":
                return moved
        log.info(f"[Framegen] patch_game: appid={appid} dll={dll_name} target={target_dir} exe={target_exe}")
        fsr4_driver = self._fsr4(game)[1]
        result = self.patch_directory(
            target_dir,
            dll_name,
            version_id=version_id,
            steam_game=marker.SteamGame(str(appid), game.name, original_options),
            fsr4_driver=fsr4_driver,
        )
        if result["status"] != "success":
            return result

        managed_options = launch_options.managed(dll_name, fsr4_driver is not None)
        log.info(f"[Framegen] patch_game success: appid={appid} launch_options={managed_options}")
        return {
            "status": "success",
            "appid": str(appid),
            "name": game.name,
            "dll_name": dll_name,
            "target_dir": str(target_dir),
            "launch_options": managed_options,
            "original_launch_options": original_options,
            "optiscaler_version": result.get("optiscaler_version"),
            "message": f"Patched {game.name} with OptiScaler {result.get('optiscaler_version')} using {dll_name}.",
        }

    def unpatch_game(self, appid: str, current_launch_options: str = "", confirmed_reset: bool = False) -> dict:
        """Unpatch a Steam game: by its record, or — for an older plugin version's patch, once the
        user confirmed what the preview showed — by resetting it."""
        try:
            return self._unpatch_game(appid, current_launch_options, confirmed_reset)
        except Exception as exc:
            log.error(f"[Framegen] unpatch_game failed for {appid}: {exc}")
            return _error(str(exc))

    def _unpatch_game(self, appid: str, current_launch_options: str, confirmed_reset: bool) -> dict:
        game = steam_library.find_game(self.home, str(appid))
        if game is None:
            return _error("Game not found in Steam library.")
        not_patched = {"status": "success", "appid": str(appid), "name": game.name, "launch_options": ""}
        if not game.install_path.exists():
            return {**not_patched, "message": "Game install directory does not exist."}
        if self._is_running(game):
            return _error("Close the game before unpatching.")
        marker_path = self._find_marker(game.install_path)
        if self._unpatch_mode(marker_path) == RESET:
            if confirmed_reset:
                return self._reset_game(appid, current_launch_options)
            if marker_path is None:
                return {**not_patched, "message": "No Framegen patch found for this game."}
            return _error(PATCHED_BY_AN_OLDER_VERSION)

        metadata = files.read_json(marker_path)
        target_dir = marker_path.parent
        result = self.unpatch_directory(target_dir)
        if result["status"] != "success":
            return result
        log.info(f"[Framegen] unpatch_game success: appid={appid} target={target_dir}")
        return {
            "status": "success",
            "appid": str(appid),
            "name": game.name,
            "launch_options": str(metadata.get("original_launch_options") or ""),
            "message": f"Unpatched {game.name}.",
        }

    # ── unpatching what an older plugin version patched ──────────────────────
    # Such a patch has no record, so Unpatch resets the directory instead: for one game the
    # user picked, shown first (preview), carried out only once the user confirms.

    def _reset_target(self, appid: str) -> tuple[steam_library.InstalledGame, Path, Path | None]:
        game = steam_library.find_game(self.home, str(appid))
        if game is None:
            raise LookupError("Game not found in Steam library.")
        if not game.install_path.exists():
            raise LookupError("Game install directory does not exist.")
        marker_path = self._find_marker(game.install_path)
        # The marker sits in the directory it patched. The path an older version wrote into it is not
        # trusted: it can name a mount point or a library location that no longer exists.
        target = marker_path.parent if marker_path is not None else self._patch_target(game)[0]
        return game, target, marker_path

    def _reset_plan(
        self, directory: Path, marker_path: Path | None, current_launch_options: str | None
    ) -> tuple[dict, tuple[plan.Operation, ...]]:
        """What resetting `directory` does, as the frontend shows it, and the operations that do it."""
        if self._is_bundle(directory):
            return _error(BUNDLE_IS_NOT_A_GAME), ()
        entries, plugin_entries = game_directory.listing(directory)
        marked_elsewhere = marker_path is not None and marker_path.parent != directory
        reset = stock_reset.plan(entries, plugin_entries, marked_elsewhere)
        if reset.evidence is None:
            return _error(f"No sign of Decky Framegen in {directory}; nothing to reset."), ()
        stored = str(files.read_json(marker_path).get("original_launch_options") or "") if marker_path else ""
        new_options = (
            stock_reset.launch_options_after_reset(current_launch_options, stored)
            if current_launch_options is not None
            else None
        )
        preview = {
            "status": "success",
            "target_dir": str(directory),
            "evidence": reset.evidence,
            "remove": list(reset.removed),
            "restore": list(reset.restored),
            "unrecoverable": list(reset.unrecoverable),
            "launch_options": new_options,
        }
        return preview, reset.operations

    def preview_unpatch_game(self, appid: str, current_launch_options: str) -> dict:
        """How unpatching a game goes: by its record (nothing to confirm), or a reset whose preview
        the user confirms first."""
        try:
            game, target, marker_path = self._reset_target(appid)
            if self._unpatch_mode(marker_path) == RECORD:
                return {"status": "success", "mode": RECORD, "name": game.name, "target_dir": str(target)}
            preview, _ = self._reset_plan(target, marker_path, current_launch_options)
            return {**preview, "mode": RESET, "name": game.name} if preview["status"] == "success" else preview
        except Exception as exc:
            log.error(f"[Framegen] preview_unpatch_game failed for {appid}: {exc}")
            return _error(str(exc))

    def _reset_game(self, appid: str, current_launch_options: str) -> dict:
        try:
            game, target, marker_path = self._reset_target(appid)
            if self._is_running(game):
                return _error("Close the game before resetting it.")
            preview, operations = self._reset_plan(target, marker_path, current_launch_options)
            if preview["status"] != "success":
                return preview
            game_directory.execute(operations, target, self.fgmod_path)
            if marker_path is not None and marker_path.exists():
                marker_path.unlink()
            self._forget(target)
            log.info(f"[Framegen] reset_game: appid={appid} target={target}")
            return {**preview, "name": game.name, "message": f"{game.name} is back to how it shipped."}
        except Exception as exc:
            log.error(f"[Framegen] reset_game failed for {appid}: {exc}")
            return _error(str(exc))

    def _reset_directory(self, target: Path) -> dict:
        try:
            preview, operations = self._reset_plan(target, None, None)
            if preview["status"] != "success":
                return preview
            game_directory.execute(operations, target, self.fgmod_path)
            self._forget(target)
            log.info(f"[Framegen] reset_directory: {target}")
            return {**preview, "message": f"{target} is back to how it shipped."}
        except Exception as exc:
            log.error(f"[Framegen] reset_directory failed for {target}: {exc}")
            return _error(str(exc))
