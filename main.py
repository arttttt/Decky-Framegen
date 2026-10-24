"""Decky entry point: exposes the plugin's backend methods to the frontend.

Each method resolves Decky's paths and delegates to a service in
py_modules/framegen; no decisions are made here.
"""

import asyncio
from pathlib import Path

import decky

from framegen.application.dev_updates import DevUpdates, Report
from framegen.application.library import Library
from framegen.application.patcher import Patcher
from framegen.domain import bundle
from framegen.infrastructure import archive, fgmod_home, github_releases


def _decky_events(event: str):
    """A report function for work running in a thread: each call becomes a Decky event to the frontend."""
    loop = asyncio.get_running_loop()

    def report(*args) -> None:
        asyncio.run_coroutine_threadsafe(decky.emit(event, *args), loop)

    return report


def _ignore(*_args) -> None:
    pass


class Plugin:
    async def _main(self):
        decky.logger.info("Framegen plugin loaded")

    async def _unload(self):
        decky.logger.info("Framegen plugin unloaded.")

    def _home_path(self) -> Path:
        return Path(str(decky.HOME))

    def _patcher(self) -> Patcher:
        return Patcher(self._home_path())

    def _dev_updates(self, report: Report = _ignore) -> DevUpdates:
        return DevUpdates(
            Path(decky.DECKY_PLUGIN_DIR),
            github_releases.list_releases,
            github_releases.download,
            Path(decky.DECKY_PLUGIN_RUNTIME_DIR) / "dev-builds",
            report,
        )

    # ── Game patching ─────────────────────────────────────────────────────────

    async def list_installed_games(self) -> dict:
        return self._patcher().list_games()

    async def manual_patch_directory(
        self,
        directory: str,
        dll_name: str = bundle.DEFAULT_PROXY_DLL,
        version_id: str = "",
    ) -> dict:
        return self._patcher().patch_user_directory(directory, dll_name, version_id or None)

    async def preview_unpatch_directory(self, directory: str) -> dict:
        return self._patcher().preview_unpatch_directory(directory)

    async def manual_unpatch_directory(self, directory: str, confirmed_reset: bool = False) -> dict:
        return self._patcher().unpatch_user_directory(directory, confirmed_reset)

    async def get_game_status(self, appid: str) -> dict:
        # Reading the game's Proton setup can take a moment on handheld storage; keep it off Decky's event loop.
        return await asyncio.to_thread(self._patcher().game_status, appid)

    async def patch_game(
        self,
        appid: str,
        dll_name: str = bundle.DEFAULT_PROXY_DLL,
        current_launch_options: str | None = "",
        version_id: str = "",
    ) -> dict:
        # None: Steam didn't say what the game's launch options are.
        return await asyncio.to_thread(
            self._patcher().patch_game, appid, dll_name, current_launch_options, version_id or None
        )

    async def preview_unpatch_game(self, appid: str, current_launch_options: str = "") -> dict:
        return self._patcher().preview_unpatch_game(appid, current_launch_options)

    async def unpatch_game(self, appid: str, current_launch_options: str = "", confirmed_reset: bool = False) -> dict:
        return self._patcher().unpatch_game(appid, current_launch_options, confirmed_reset)

    # ── OptiScaler library ────────────────────────────────────────────────────

    def _library(self, report=_ignore) -> Library:
        patcher = self._patcher()
        return Library(
            self._home_path() / "fgmod",
            Path(decky.DECKY_PLUGIN_DIR) / archive.SEVEN_ZIP,
            github_releases.list_releases,
            github_releases.download,
            report,
            lambda: fgmod_home.refresh_core(self._home_path() / "fgmod", Path(decky.DECKY_PLUGIN_DIR) / "assets"),
            patcher.games_using,
            patcher.games_linked_to,
        )

    async def library_installed(self) -> dict:
        return self._library().installed()

    async def library_removal(self, version_id: str) -> dict:
        return await asyncio.to_thread(self._library().removal, version_id)

    async def library_versions(self, channel: str) -> dict:
        return await asyncio.to_thread(self._library().versions, channel)

    async def library_install(self, channel: str, version_id: str) -> dict:
        # Download progress goes to the frontend as "library_download" events.
        library = self._library(_decky_events("library_download"))
        return await asyncio.to_thread(library.install, channel, version_id)

    async def library_reinstall(self, version_id: str) -> dict:
        # Progress goes to the frontend as "library_download" events, as for an install.
        library = self._library(_decky_events("library_download"))
        return await asyncio.to_thread(library.reinstall, version_id)

    async def library_remove(self, version_id: str) -> dict:
        # Deleting an unpacked version (hundreds of MB) takes a moment on handheld storage.
        return await asyncio.to_thread(self._library().remove, version_id)

    # ── Development builds ────────────────────────────────────────────────────

    async def get_dev_build(self) -> dict:
        return self._dev_updates().build()

    async def list_dev_builds(self) -> dict:
        # The request to GitHub can take seconds; keep it off Decky's event loop.
        return await asyncio.to_thread(self._dev_updates().available_builds)

    async def dev_install_request(self, channel: str) -> dict:
        # Asks GitHub again and downloads the build off Decky's event loop; progress goes
        # back to the frontend as "dev_build_download" events.
        updates = self._dev_updates(_decky_events("dev_build_download"))
        return await asyncio.to_thread(updates.install_request, channel)

    # ── Misc ──────────────────────────────────────────────────────────────────

    async def get_path_defaults(self) -> dict:
        return self._patcher().path_defaults()

    async def log_error(self, error: str) -> None:
        decky.logger.error(f"FRONTEND: {error}")
