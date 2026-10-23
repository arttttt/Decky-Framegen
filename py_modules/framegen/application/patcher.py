"""Patching and unpatching games: the one owner of the patch lifecycle.

Manual directory patching and Steam AppID patching are two entry points into
the same plan-and-execute path. Results are the plain dicts the frontend reads.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from framegen.domain import bundle, exe_target, launch_options, marker, patch_record, steam, stock_reset
from framegen.domain import patch_plan as plan
from framegen.infrastructure import bundle_store, files, game_directory, processes
from framegen.infrastructure import steam as steam_library

log = logging.getLogger(__name__)

NOT_INSTALLED = "OptiScaler bundle not installed. Run Install first."
BUNDLE_IS_NOT_A_GAME = "The target directory is the OptiScaler bundle itself. Aborting to prevent accidental deletion."
PATCHED_BY_AN_OLDER_VERSION = (
    "This game was patched by an older version of the plugin. Use Reset to stock to remove that patch first."
)


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


class Patcher:
    def __init__(self, home: Path):
        self.home = home
        self.fgmod_path = home / "fgmod"

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
        fsr4_variant: str | None,
        *,
        reset_ini: bool = False,
        steam_game: marker.SteamGame | None = None,
    ) -> dict:
        """Patch a directory and leave our marker in it, which later proves which files are ours."""
        if dll_name not in bundle.VALID_DLL_NAMES:
            return _error(f"Invalid proxy DLL name: {dll_name}")
        if not self.fgmod_path.exists():
            return _error(NOT_INSTALLED)
        previous_variant = str(files.read_json(directory / bundle.MARKER_FILENAME).get("fsr4_variant") or "").strip()
        carried_over: frozenset[str] = frozenset()
        if (directory / bundle.MARKER_FILENAME).exists():
            # A repatch first undoes the previous patch, exactly as its marker records it, keeping
            # the OptiScaler.ini it placed (the user's settings) unless asked to reset it.
            previous = patch_record.parse(files.read_json(directory / bundle.MARKER_FILENAME))
            if previous is not None and not reset_ini and plan.INI_FILENAME in {p.path for p in previous.placed}:
                carried_over = frozenset({plan.INI_FILENAME})
            undone = self.unpatch_directory(directory, keep=carried_over)
            if undone["status"] != "success":
                return undone
        variant = bundle_store.selected_variant(self.fgmod_path, fsr4_variant)
        label = bundle.FSR4_VARIANTS[variant]["label"]
        request = plan.PatchRequest(dll_name, variant, reset_ini)
        try:
            game = game_directory.read(directory, previous_variant)
            patch = plan.plan_patch(game, game_directory.bundle_files(self.fgmod_path), request)
            upscaler_sha256 = files.sha256(self.fgmod_path / patch.upscaler_source)
            log.info(f"Patching {directory} with {dll_name} and FSR4 variant {variant} ({label})")
            recorded = patch_record.record(
                patch.operations,
                game.entries,
                game_directory.bundle_hashes(self.fgmod_path, patch.operations),
                carried_over & game.entries,
            )
            optiscaler_version = bundle_store.optiscaler_version(self.fgmod_path)
            details = marker.build(
                dll_name=dll_name,
                target_dir=directory,
                backed_up_files=[backup.original for backup in recorded.backups],
                optiscaler_version=optiscaler_version,
                fsr4_variant=variant,
                fsr4_upscaler_sha256=upscaler_sha256,
                patched_at=datetime.now(timezone.utc).isoformat(),
                steam_game=steam_game,
            )
            marker_path = directory / bundle.MARKER_FILENAME
            # The record lands before the first file does, so even an interrupted patch can be undone.
            files.write_json(marker_path, {**details, **patch_record.to_json(recorded, complete=False)})
            game_directory.execute(patch.operations, directory, self.fgmod_path)
            files.write_json(marker_path, {**details, **patch_record.to_json(recorded, complete=True)})
        except plan.PlanError as exc:
            return _error(str(exc))
        except PermissionError as exc:
            log.error(f"Manual patch permission error: {exc}")
            return _error(f"Permission error while patching: {exc}")
        except Exception as exc:
            log.error(f"Manual patch failed: {exc}")
            return _error(f"Manual patch failed: {exc}")
        return {
            "status": "success",
            "message": f"OptiScaler files copied to {directory} using {label}",
            "fsr4_variant": variant,
            "fsr4_variant_label": label,
            "fsr4_upscaler_sha256": upscaler_sha256,
            "optiscaler_version": optiscaler_version,
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
        return {"status": "success", "message": f"OptiScaler files removed from {directory}"}

    def patch_user_directory(self, directory: str, dll_name: str, fsr4_variant: str) -> dict:
        try:
            target = self.resolve_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            log.error(f"Manual patch validation failed: {exc}")
            return _error(str(exc))
        return self.patch_directory(target, dll_name, fsr4_variant)

    def unpatch_user_directory(self, directory: str) -> dict:
        try:
            target = self.resolve_directory(directory)
        except (FileNotFoundError, NotADirectoryError, PermissionError) as exc:
            log.error(f"Manual unpatch validation failed: {exc}")
            return _error(str(exc))
        return self.unpatch_directory(target)

    def path_defaults(self) -> dict:
        """Starting points for the manual directory picker."""
        native_steam = steam.steam_root_candidates(self.home)[0]
        return {"home": str(self.home), "steam_common": str(native_steam / "steamapps" / "common")}

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

    def _patch_target(self, game: steam_library.InstalledGame) -> tuple[Path, Path | None]:
        candidates = steam_library.executables(game.install_path)
        running = self._running_executable(candidates)
        return exe_target.patch_target(game.install_path, game.name, candidates, running)

    @staticmethod
    def _find_marker(install_root: Path) -> Path | None:
        if not install_root.exists():
            return None
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
            "fsr4_variant": None,
            "fsr4_variant_label": None,
        }
        if game is None:
            return {**unpatched, "install_found": False, "message": "Game not found in Steam library."}
        if not game.install_path.exists():
            return {**unpatched, "name": game.name, "install_found": False, "message": "Game install directory not found."}
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
        target_dir = Path(metadata.get("target_dir", str(marker_path.parent)))
        dll_present = (target_dir / dll_name).exists()
        upscaler_path = target_dir / bundle.FSR4_UPSCALER_FILENAME
        upscaler_sha256 = files.sha256(upscaler_path) if upscaler_path.exists() else None
        extra_hashes = {
            name: files.sha256(target_dir / name)
            for name in bundle.VARIANT_EXTRA_FILENAMES
            if (target_dir / name).exists()
        }
        stored_variant = str(metadata.get("fsr4_variant") or "").strip() or None
        variant = bundle.detect_variant(upscaler_sha256, extra_hashes) or (
            stored_variant if stored_variant in bundle.FSR4_VARIANTS else None
        )
        label = bundle.FSR4_VARIANTS[variant]["label"] if variant else None
        if dll_present:
            message = f"Patched using {dll_name}" + (f" with {label}." if label else ".")
        else:
            message = f"Marker found but {dll_name} is missing. Reinstall recommended."
        return {
            "status": "success",
            "appid": str(appid),
            "name": game.name,
            "install_found": True,
            "patched": dll_present,
            "dll_name": dll_name,
            "target_dir": str(target_dir),
            "patched_at": metadata.get("patched_at"),
            "optiscaler_version": metadata.get("optiscaler_version"),
            "fsr4_variant": variant,
            "fsr4_variant_label": label,
            "fsr4_upscaler_sha256": upscaler_sha256,
            "message": message,
        }

    def patch_game(self, appid: str, dll_name: str, current_launch_options: str, fsr4_variant: str) -> dict:
        try:
            return self._patch_game(appid, dll_name, current_launch_options, fsr4_variant)
        except Exception as exc:
            log.error(f"[Framegen] patch_game failed for {appid}: {exc}")
            return _error(str(exc))

    def _patch_game(self, appid: str, dll_name: str, current_launch_options: str, fsr4_variant: str) -> dict:
        game = steam_library.find_game(self.home, str(appid))
        if game is None:
            return _error("Game not found in Steam library.")
        if not game.install_path.exists():
            return _error("Game install directory does not exist.")
        if self._is_running(game):
            return _error("Close the game before patching.")
        if not self.fgmod_path.exists():
            return _error(NOT_INSTALLED)

        existing_marker = self._find_marker(game.install_path)
        existing = files.read_json(existing_marker) if existing_marker else {}
        original_options = marker.original_launch_options(
            current_launch_options, str(existing.get("original_launch_options") or "")
        )

        target_dir, target_exe = self._patch_target(game)
        if existing_marker and existing_marker.parent != target_dir:
            # The game's executable moved since its last patch; that directory is undone first.
            moved = self.unpatch_directory(existing_marker.parent)
            if moved["status"] != "success":
                return moved
        log.info(f"[Framegen] patch_game: appid={appid} dll={dll_name} target={target_dir} exe={target_exe}")
        result = self.patch_directory(
            target_dir, dll_name, fsr4_variant, steam_game=marker.SteamGame(str(appid), game.name, original_options)
        )
        if result["status"] != "success":
            return result

        managed_options = launch_options.managed(dll_name)
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
            "fsr4_variant": result.get("fsr4_variant"),
            "fsr4_variant_label": result.get("fsr4_variant_label"),
            "fsr4_upscaler_sha256": result.get("fsr4_upscaler_sha256"),
            "message": f"Patched {game.name} using {dll_name} with {result.get('fsr4_variant_label')}.",
        }

    def unpatch_game(self, appid: str) -> dict:
        try:
            return self._unpatch_game(appid)
        except Exception as exc:
            log.error(f"[Framegen] unpatch_game failed for {appid}: {exc}")
            return _error(str(exc))

    def _unpatch_game(self, appid: str) -> dict:
        game = steam_library.find_game(self.home, str(appid))
        if game is None:
            return _error("Game not found in Steam library.")
        not_patched = {"status": "success", "appid": str(appid), "name": game.name, "launch_options": ""}
        if not game.install_path.exists():
            return {**not_patched, "message": "Game install directory does not exist."}
        if self._is_running(game):
            return _error("Close the game before unpatching.")
        marker_path = self._find_marker(game.install_path)
        if marker_path is None:
            return {**not_patched, "message": "No Framegen patch found for this game."}

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

    # ── reset to stock ───────────────────────────────────────────────────────
    # For games an earlier plugin version patched: one game the user picked, shown
    # first (preview), carried out only when the user confirms (reset).

    def _reset_target(self, appid: str) -> tuple[steam_library.InstalledGame, Path, Path | None]:
        game = steam_library.find_game(self.home, str(appid))
        if game is None:
            raise LookupError("Game not found in Steam library.")
        if not game.install_path.exists():
            raise LookupError("Game install directory does not exist.")
        marker_path = self._find_marker(game.install_path)
        if marker_path is not None:
            target = Path(files.read_json(marker_path).get("target_dir") or marker_path.parent)
        else:
            target, _ = self._patch_target(game)
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

    def preview_reset_game(self, appid: str, current_launch_options: str) -> dict:
        try:
            game, target, marker_path = self._reset_target(appid)
            preview, _ = self._reset_plan(target, marker_path, current_launch_options)
            return {**preview, "name": game.name}
        except Exception as exc:
            log.error(f"[Framegen] preview_reset_game failed for {appid}: {exc}")
            return _error(str(exc))

    def reset_game(self, appid: str, current_launch_options: str) -> dict:
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
            log.info(f"[Framegen] reset_game: appid={appid} target={target}")
            return {**preview, "name": game.name, "message": f"{game.name} is back to how it shipped."}
        except Exception as exc:
            log.error(f"[Framegen] reset_game failed for {appid}: {exc}")
            return _error(str(exc))

    def preview_reset_directory(self, directory: str) -> dict:
        try:
            preview, _ = self._reset_plan(self.resolve_directory(directory), None, None)
            return preview
        except Exception as exc:
            log.error(f"[Framegen] preview_reset_directory failed for {directory}: {exc}")
            return _error(str(exc))

    def reset_directory(self, directory: str) -> dict:
        try:
            target = self.resolve_directory(directory)
            preview, operations = self._reset_plan(target, None, None)
            if preview["status"] != "success":
                return preview
            game_directory.execute(operations, target, self.fgmod_path)
            log.info(f"[Framegen] reset_directory: {target}")
            return {**preview, "message": f"{target} is back to how it shipped."}
        except Exception as exc:
            log.error(f"[Framegen] reset_directory failed for {directory}: {exc}")
            return _error(str(exc))
