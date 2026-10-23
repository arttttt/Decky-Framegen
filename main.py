"""Decky entry point: exposes the plugin's backend methods to the frontend.

Each method resolves Decky's paths and delegates to a service in
py_modules/framegen; no decisions are made here.
"""

from pathlib import Path

import decky

from framegen.application.installer import Installer
from framegen.application.patcher import Patcher
from framegen.domain import bundle


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

    # ── Misc ──────────────────────────────────────────────────────────────────

    async def get_path_defaults(self) -> dict:
        return self._patcher().path_defaults()

    async def log_error(self, error: str) -> None:
        decky.logger.error(f"FRONTEND: {error}")
