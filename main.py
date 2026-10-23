"""Decky entry point: exposes the plugin's backend methods to the frontend.

Each method resolves Decky's paths and delegates to a service in
py_modules/framegen; no decisions are made here.
"""

import asyncio
from pathlib import Path

import decky

from framegen.application.dev_updates import DevUpdates, Report
from framegen.application.installer import Installer
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

    def _installer(self) -> Installer:
        return Installer(self._home_path(), Path(decky.DECKY_PLUGIN_DIR))

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

    # ── OptiScaler bundle ─────────────────────────────────────────────────────

    async def run_install_fgmod(self, selected_default_variant: str = bundle.DEFAULT_FSR4_VARIANT) -> dict:
        return self._installer().install(selected_default_variant)

    async def run_uninstall_fgmod(self) -> dict:
        return self._installer().uninstall()

    async def set_default_fsr4_variant(self, selected_default_variant: str = bundle.DEFAULT_FSR4_VARIANT) -> dict:
        return self._installer().switch_default(selected_default_variant)

    async def check_fgmod_path(self) -> dict:
        return self._installer().status()

    # ── Game patching ─────────────────────────────────────────────────────────

    async def list_installed_games(self) -> dict:
        return self._patcher().list_games()

    async def manual_patch_directory(
        self,
        directory: str,
        dll_name: str = bundle.DEFAULT_PROXY_DLL,
        fsr4_variant: str = bundle.DEFAULT_FSR4_VARIANT,
    ) -> dict:
        return self._patcher().patch_user_directory(directory, dll_name, fsr4_variant)

    async def manual_unpatch_directory(self, directory: str) -> dict:
        return self._patcher().unpatch_user_directory(directory)

    async def get_game_status(self, appid: str) -> dict:
        return self._patcher().game_status(appid)

    async def patch_game(
        self,
        appid: str,
        dll_name: str = bundle.DEFAULT_PROXY_DLL,
        current_launch_options: str = "",
        fsr4_variant: str = bundle.DEFAULT_FSR4_VARIANT,
    ) -> dict:
        return self._patcher().patch_game(appid, dll_name, current_launch_options, fsr4_variant)

    async def unpatch_game(self, appid: str) -> dict:
        return self._patcher().unpatch_game(appid)

    # ── OptiScaler library ────────────────────────────────────────────────────

    def _library(self, report=_ignore) -> Library:
        return Library(
            self._home_path() / "fgmod",
            Path(decky.DECKY_PLUGIN_DIR) / archive.SEVEN_ZIP,
            github_releases.list_releases,
            github_releases.download,
            report,
            lambda: fgmod_home.refresh_core(self._home_path() / "fgmod", Path(decky.DECKY_PLUGIN_DIR) / "assets"),
        )

    async def library_versions(self, channel: str) -> dict:
        return await asyncio.to_thread(self._library().versions, channel)

    async def library_install(self, channel: str, version_id: str) -> dict:
        # Download progress goes to the frontend as "library_download" events.
        library = self._library(_decky_events("library_download"))
        return await asyncio.to_thread(library.install, channel, version_id)

    async def library_remove(self, version_id: str) -> dict:
        return self._library().remove(version_id)

    async def library_set_default(self, version_id: str) -> dict:
        return self._library().set_default(version_id)

    # ── Reset to stock (one game, on the user's request) ─────────────────────

    async def preview_reset_game(self, appid: str, current_launch_options: str = "") -> dict:
        return self._patcher().preview_reset_game(appid, current_launch_options)

    async def reset_game(self, appid: str, current_launch_options: str = "") -> dict:
        return self._patcher().reset_game(appid, current_launch_options)

    async def preview_reset_directory(self, directory: str) -> dict:
        return self._patcher().preview_reset_directory(directory)

    async def reset_directory(self, directory: str) -> dict:
        return self._patcher().reset_directory(directory)

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
