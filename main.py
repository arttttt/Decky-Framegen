import decky
import os
import subprocess
import json
import shutil
import re
import filecmp
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from framegen.application.patcher import Patcher
from framegen.domain import bundle, ini
from framegen.infrastructure import bundle_store, files, game_directory




class Plugin:
    async def _main(self):
        decky.logger.info("Framegen plugin loaded")

    async def _unload(self):
        decky.logger.info("Framegen plugin unloaded.")
        
    def _create_renamed_copies(self, source_file, renames_dir):
        """Create renamed copies of the OptiScaler.dll file"""
        try:
            renames_dir.mkdir(exist_ok=True)
            
            rename_files = [
                "dxgi.dll",
                "winmm.dll",
                "dbghelp.dll",
                "version.dll",
                "wininet.dll",
                "winhttp.dll",
                "OptiScaler.asi"
            ]
            
            if source_file.exists():
                for rename_file in rename_files:
                    dest_file = renames_dir / rename_file
                    shutil.copy2(source_file, dest_file)
                    decky.logger.info(f"Created renamed copy: {dest_file}")
                return True
            else:
                decky.logger.error(f"Source file {source_file} does not exist")
                return False
                
        except Exception as e:
            decky.logger.error(f"Failed to create renamed copies: {e}")
            return False
    
    def _copy_launcher_scripts(self, assets_dir, extract_path):
        """Copy launcher scripts from assets directory"""
        try:
            # Copy fgmod script
            fgmod_script_src = assets_dir / "fgmod.sh"
            fgmod_script_dest = extract_path / "fgmod"
            if fgmod_script_src.exists():
                shutil.copy2(fgmod_script_src, fgmod_script_dest)
                fgmod_script_dest.chmod(0o755)
                decky.logger.info(f"Copied fgmod script to {fgmod_script_dest}")
            
            # Copy uninstaller script
            uninstaller_src = assets_dir / "fgmod-uninstaller.sh"
            uninstaller_dest = extract_path / "fgmod-uninstaller.sh"
            if uninstaller_src.exists():
                shutil.copy2(uninstaller_src, uninstaller_dest)
                uninstaller_dest.chmod(0o755)
                decky.logger.info(f"Copied uninstaller script to {uninstaller_dest}")

            # Copy optiscaler config updater script
            optiscaler_config_updater_src = assets_dir / "update-optiscaler-config.py"
            optiscaler_config_updater_dest = extract_path / "update-optiscaler-config.py"
            if optiscaler_config_updater_src.exists():
                shutil.copy2(optiscaler_config_updater_src, optiscaler_config_updater_dest)
                optiscaler_config_updater_dest.chmod(0o755)
                decky.logger.info(f"Copied update-optiscaler-config.py script to {optiscaler_config_updater_dest}")
                
            return True
        except Exception as e:
            decky.logger.error(f"Failed to copy launcher scripts: {e}")
            return False
    







    def _extract_archive(self, archive_path: Path, output_dir: Path, members: list[str] | None = None) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        extract_cmd = [
            "7z",
            "x",
            "-y",
            "-o" + str(output_dir),
            str(archive_path),
        ]
        if members:
            extract_cmd.extend(members)

        clean_env = os.environ.copy()
        clean_env["LD_LIBRARY_PATH"] = ""
        result = subprocess.run(
            extract_cmd,
            capture_output=True,
            text=True,
            check=False,
            env=clean_env,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr or result.stdout or f"Failed to extract {archive_path.name}")

    def _verify_bundled_asset(self, path: Path, expected_sha256: str, description: str) -> str:
        actual_sha256 = files.sha256(path)
        if actual_sha256.lower() != expected_sha256.lower():
            raise RuntimeError(
                f"{description} hash mismatch: expected {expected_sha256}, got {actual_sha256}"
            )
        return actual_sha256
















    def _sync_variant_root_extra_files(self, fgmod_path: Path, fsr4_variant: str | None) -> None:
        selected_extra_files = {extra_file["name"]: extra_file for extra_file in bundle.variant_extra_files(fsr4_variant)}
        for filename in bundle.VARIANT_EXTRA_FILENAMES:
            root_path = fgmod_path / filename
            if filename not in selected_extra_files:
                if root_path.exists():
                    root_path.unlink()
                continue
            source_path = bundle.variant_extra_file_path(fgmod_path, fsr4_variant, filename)
            if not source_path.exists():
                raise FileNotFoundError(f"Prepared FSR4 variant extra file missing: {source_path}")
            shutil.copy2(source_path, root_path)

    def _activate_default_fsr4_variant(self, fgmod_path: Path, fsr4_variant: str | None) -> str:
        variant_id = bundle.normalize_variant(fsr4_variant)
        variant_path = bundle.variant_upscaler_path(fgmod_path, variant_id)
        if not variant_path.exists():
            raise FileNotFoundError(f"Prepared FSR4 variant missing: {variant_path}")
        shutil.copy2(variant_path, fgmod_path / bundle.FSR4_UPSCALER_FILENAME)
        self._sync_variant_root_extra_files(fgmod_path, variant_id)
        return variant_id









    async def extract_static_optiscaler(self, selected_default_variant: str = bundle.DEFAULT_FSR4_VARIANT) -> dict:
        """Prepare the shared ~/fgmod bundle with all bundled FSR4 runtime variants."""
        try:
            decky.logger.info("Starting extract_static_optiscaler method")

            bin_path = Path(decky.DECKY_PLUGIN_DIR) / "bin"
            extract_path = Path(decky.HOME) / "fgmod"
            assets_dir = Path(decky.DECKY_PLUGIN_DIR) / "assets"
            selected_default_variant = bundle.normalize_variant(selected_default_variant)

            if not bin_path.exists():
                return {"status": "error", "message": f"Bin directory not found: {bin_path}"}

            optiscaler_archive = bin_path / bundle.OPTISCALER_ARCHIVE_ASSET["name"]
            fsr4_int8_src = bin_path / bundle.FSR4_INT8_ASSET["name"]
            fsr4_official_411_src = bin_path / bundle.FSR4_OFFICIAL_411_ASSET["name"]
            fsr4_valve_411_src = bin_path / bundle.FSR4_VALVE_411_ASSET["name"]
            amdxc64_rdna2_src = bin_path / bundle.AMDXC64_RDNA2_ASSET["name"]
            optiscaler_pre10_src = bin_path / bundle.OPTISCALER_PRE10_ASSET["name"]
            optipatcher_src = bin_path / bundle.OPTIPATCHER_ASSET["name"]
            for required_path, asset in [
                (optiscaler_archive, bundle.OPTISCALER_ARCHIVE_ASSET),
                (fsr4_int8_src, bundle.FSR4_INT8_ASSET),
                (fsr4_official_411_src, bundle.FSR4_OFFICIAL_411_ASSET),
                (fsr4_valve_411_src, bundle.FSR4_VALVE_411_ASSET),
                (amdxc64_rdna2_src, bundle.AMDXC64_RDNA2_ASSET),
                (optiscaler_pre10_src, bundle.OPTISCALER_PRE10_ASSET),
                (optipatcher_src, bundle.OPTIPATCHER_ASSET),
            ]:
                if not required_path.exists():
                    return {
                        "status": "error",
                        "message": f"Required bundled asset missing: {asset['name']}",
                    }
                self._verify_bundled_asset(required_path, asset["sha256"], asset["name"])

            if extract_path.exists():
                shutil.rmtree(extract_path)
            extract_path.mkdir(parents=True, exist_ok=True)

            self._extract_archive(optiscaler_archive, extract_path)

            source_file = extract_path / "OptiScaler.dll"
            renames_dir = extract_path / "renames"
            if not self._create_renamed_copies(source_file, renames_dir):
                return {"status": "error", "message": "Failed to prepare renamed OptiScaler proxies."}

            if not self._copy_launcher_scripts(assets_dir, extract_path):
                return {"status": "error", "message": "Failed to copy launcher scripts."}

            plugins_dir = extract_path / "plugins"
            plugins_dir.mkdir(parents=True, exist_ok=True)
            optipatcher_dst = plugins_dir / "OptiPatcher.asi"
            shutil.copy2(optipatcher_src, optipatcher_dst)
            optipatcher_sha256 = self._verify_bundled_asset(
                optipatcher_dst,
                bundle.OPTIPATCHER_ASSET["sha256"],
                "Prepared OptiPatcher plugin",
            )

            ini_file = extract_path / "OptiScaler.ini"
            game_directory.edit_ini(ini_file, ini.apply_bundle_defaults, "apply plugin defaults")

            native_upscaler_root = extract_path / bundle.FSR4_UPSCALER_FILENAME
            native_upscaler_sha256 = self._verify_bundled_asset(
                native_upscaler_root,
                bundle.FSR4_VARIANTS["rdna4-native"]["sha256"],
                "Archive-native FSR4 upscaler",
            )

            rdna4_dir = extract_path / bundle.FSR4_VARIANTS["rdna4-native"]["dir_name"]
            rdna4_dir.mkdir(parents=True, exist_ok=True)
            rdna4_upscaler = rdna4_dir / bundle.FSR4_UPSCALER_FILENAME
            shutil.copy2(native_upscaler_root, rdna4_upscaler)
            self._verify_bundled_asset(
                rdna4_upscaler,
                bundle.FSR4_VARIANTS["rdna4-native"]["sha256"],
                "Prepared rdna4-native FSR4 upscaler",
            )

            official_411_dir = extract_path / bundle.FSR4_VARIANTS["rdna34-official-411"]["dir_name"]
            official_411_dir.mkdir(parents=True, exist_ok=True)
            official_411_upscaler = official_411_dir / bundle.FSR4_UPSCALER_FILENAME
            shutil.copy2(native_upscaler_root, official_411_upscaler)
            self._verify_bundled_asset(
                official_411_upscaler,
                bundle.FSR4_VARIANTS["rdna34-official-411"]["sha256"],
                "Prepared rdna34-official-411 FSR4 upscaler",
            )
            self._verify_bundled_asset(
                fsr4_official_411_src,
                bundle.FSR4_OFFICIAL_411_ASSET["sha256"],
                "Bundled rdna34-official-411 driver override",
            )
            official_411_driver = official_411_dir / bundle.FSR4_DRIVER_OVERRIDE_FILENAME
            shutil.copy2(fsr4_official_411_src, official_411_driver)
            self._verify_bundled_asset(
                official_411_driver,
                bundle.FSR4_OFFICIAL_411_ASSET["sha256"],
                "Prepared rdna34-official-411 driver override",
            )

            rdna2_valve_dir = extract_path / bundle.FSR4_VARIANTS["rdna2-valve-411-pre10"]["dir_name"]
            rdna2_valve_dir.mkdir(parents=True, exist_ok=True)
            rdna2_valve_upscaler = rdna2_valve_dir / bundle.FSR4_UPSCALER_FILENAME
            shutil.copy2(native_upscaler_root, rdna2_valve_upscaler)
            self._verify_bundled_asset(
                rdna2_valve_upscaler,
                bundle.FSR4_VARIANTS["rdna2-valve-411-pre10"]["sha256"],
                "Prepared rdna2-valve-411-pre10 FSR4 upscaler",
            )
            self._verify_bundled_asset(
                fsr4_valve_411_src,
                bundle.FSR4_VALVE_411_ASSET["sha256"],
                "Bundled rdna2-valve-411-pre10 driver override",
            )
            rdna2_valve_driver = rdna2_valve_dir / bundle.FSR4_DRIVER_OVERRIDE_FILENAME
            shutil.copy2(fsr4_valve_411_src, rdna2_valve_driver)
            self._verify_bundled_asset(
                rdna2_valve_driver,
                bundle.FSR4_VALVE_411_ASSET["sha256"],
                "Prepared rdna2-valve-411-pre10 driver override",
            )
            self._verify_bundled_asset(
                amdxc64_rdna2_src,
                bundle.AMDXC64_RDNA2_ASSET["sha256"],
                "Bundled rdna2-valve-411-pre10 amdxc64 override",
            )
            rdna2_valve_amdxc64 = rdna2_valve_dir / "amdxc64.dll"
            shutil.copy2(amdxc64_rdna2_src, rdna2_valve_amdxc64)
            self._verify_bundled_asset(
                rdna2_valve_amdxc64,
                bundle.AMDXC64_RDNA2_ASSET["sha256"],
                "Prepared rdna2-valve-411-pre10 amdxc64 override",
            )
            self._verify_bundled_asset(
                optiscaler_pre10_src,
                bundle.OPTISCALER_PRE10_ASSET["sha256"],
                "Bundled rdna2-valve-411-pre10 OptiScaler injector",
            )
            rdna2_valve_injector = rdna2_valve_dir / "OptiScaler.dll"
            shutil.copy2(optiscaler_pre10_src, rdna2_valve_injector)
            self._verify_bundled_asset(
                rdna2_valve_injector,
                bundle.OPTISCALER_PRE10_ASSET["sha256"],
                "Prepared rdna2-valve-411-pre10 OptiScaler injector",
            )
            if not self._create_renamed_copies(rdna2_valve_injector, rdna2_valve_dir / "renames"):
                return {"status": "error", "message": "Failed to prepare renamed pre10 OptiScaler proxies."}

            rdna23_dir = extract_path / bundle.FSR4_VARIANTS["rdna23-int8"]["dir_name"]
            rdna23_dir.mkdir(parents=True, exist_ok=True)
            self._verify_bundled_asset(
                fsr4_int8_src,
                bundle.FSR4_VARIANTS["rdna23-int8"]["sha256"],
                "Bundled rdna23-int8 FSR4 upscaler",
            )
            shutil.copy2(fsr4_int8_src, rdna23_dir / bundle.FSR4_UPSCALER_FILENAME)
            self._verify_bundled_asset(
                rdna23_dir / bundle.FSR4_UPSCALER_FILENAME,
                bundle.FSR4_VARIANTS["rdna23-int8"]["sha256"],
                "Prepared rdna23-int8 FSR4 upscaler",
            )

            selected_default_variant = self._activate_default_fsr4_variant(extract_path, selected_default_variant)
            active_upscaler_sha256 = files.sha256(extract_path / bundle.FSR4_UPSCALER_FILENAME)

            version_file = extract_path / bundle.VERSION_FILENAME
            version_file.write_text(bundle.OPTISCALER_ARCHIVE_ASSET["version"], encoding="utf-8")

            install_manifest = {
                "schema_version": 1,
                "installed_at": datetime.now(timezone.utc).isoformat(),
                "optiscaler": {
                    "asset_name": bundle.OPTISCALER_ARCHIVE_ASSET["name"],
                    "version": bundle.OPTISCALER_ARCHIVE_ASSET["version"],
                    "sha256": bundle.OPTISCALER_ARCHIVE_ASSET["sha256"],
                    "native_upscaler_sha256": native_upscaler_sha256,
                },
                "optipatcher": {
                    "asset_name": bundle.OPTIPATCHER_ASSET["name"],
                    "version": bundle.OPTIPATCHER_ASSET["version"],
                    "sha256": optipatcher_sha256,
                    "target_path": str(optipatcher_dst.relative_to(extract_path)),
                },
                "fsr4_variants": {
                    variant_id: {
                        "label": variant["label"],
                        "dir_name": variant["dir_name"],
                        "path": str((Path(variant["dir_name"]) / bundle.FSR4_UPSCALER_FILENAME).as_posix()),
                        "sha256": variant["sha256"],
                        "source_asset_name": variant["source_asset_name"],
                        "source_version": variant["source_version"],
                        "uses_archive_native": bool(variant["uses_archive_native"]),
                        "injector": (
                            {
                                "name": variant["injector"]["name"],
                                "sha256": variant["injector"]["sha256"],
                                "source_asset_name": variant["injector"]["source_asset_name"],
                                "source_version": variant["injector"]["source_version"],
                                "path": str((Path(variant["dir_name"]) / variant["injector"]["name"]).as_posix()),
                            }
                            if isinstance(variant.get("injector"), dict)
                            else None
                        ),
                        "config_overrides": dict(variant.get("config_overrides") or {}),
                        "extra_files": [
                            {
                                "name": extra_file["name"],
                                "sha256": extra_file["sha256"],
                                "source_asset_name": extra_file["source_asset_name"],
                                "source_version": extra_file["source_version"],
                                "path": str((Path(variant["dir_name"]) / extra_file["name"]).as_posix()),
                            }
                            for extra_file in variant.get("extra_files", [])
                        ],
                    }
                    for variant_id, variant in bundle.FSR4_VARIANTS.items()
                },
                "selected_default_variant": selected_default_variant,
                "active_root_upscaler": {
                    "path": bundle.FSR4_UPSCALER_FILENAME,
                    "sha256": active_upscaler_sha256,
                    "variant": selected_default_variant,
                },
            }
            files.write_json(bundle_store.manifest_path(extract_path), install_manifest)

            return {
                "status": "success",
                "message": f"Successfully extracted OptiScaler {bundle.OPTISCALER_ARCHIVE_ASSET['version']} to ~/fgmod",
                "version": bundle.OPTISCALER_ARCHIVE_ASSET["version"],
                "selected_default_variant": selected_default_variant,
                "selected_default_variant_label": bundle.FSR4_VARIANTS[selected_default_variant]["label"],
            }
        except Exception as e:
            decky.logger.error(f"Extract failed with exception: {str(e)}")
            import traceback
            decky.logger.error(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": f"Extract failed: {str(e)}"}

    async def run_uninstall_fgmod(self) -> dict:
        try:
            # Remove fgmod directory
            fgmod_path = Path(decky.HOME) / "fgmod"
            
            if fgmod_path.exists():
                shutil.rmtree(fgmod_path)
                decky.logger.info(f"Removed directory: {fgmod_path}")
                return {
                    "status": "success", 
                    "output": "Successfully removed fgmod directory"
                }
            else:
                return {
                    "status": "success", 
                    "output": "No fgmod directory found to remove"
                }
            
        except Exception as e:
            decky.logger.error(f"Uninstall error: {str(e)}")
            return {
                "status": "error", 
                "message": f"Uninstall failed: {str(e)}", 
                "output": str(e)
            }

    async def set_default_fsr4_variant(self, selected_default_variant: str = bundle.DEFAULT_FSR4_VARIANT) -> dict:
        try:
            fgmod_path = Path(decky.HOME) / "fgmod"
            if not fgmod_path.exists():
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}

            selected_default_variant = bundle.normalize_variant(selected_default_variant)
            manifest = bundle_store.load_manifest(fgmod_path)
            if not manifest:
                return {"status": "error", "message": "Install manifest missing. Reinstall OptiScaler."}

            selected_default_variant = self._activate_default_fsr4_variant(fgmod_path, selected_default_variant)
            active_upscaler_sha256 = files.sha256(fgmod_path / bundle.FSR4_UPSCALER_FILENAME)
            manifest["selected_default_variant"] = selected_default_variant
            manifest["active_root_upscaler"] = {
                "path": bundle.FSR4_UPSCALER_FILENAME,
                "sha256": active_upscaler_sha256,
                "variant": selected_default_variant,
            }
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            files.write_json(bundle_store.manifest_path(fgmod_path), manifest)
            return {
                "status": "success",
                "output": f"Default FSR4 runtime switched to {bundle.FSR4_VARIANTS[selected_default_variant]['label']}.",
                "version": bundle_store.optiscaler_version(fgmod_path),
                "selected_default_variant": selected_default_variant,
                "selected_default_variant_label": bundle.FSR4_VARIANTS[selected_default_variant]["label"],
            }
        except Exception as e:
            decky.logger.error(f"Failed to switch default FSR4 runtime: {e}")
            return {"status": "error", "message": f"Failed to switch default FSR4 runtime: {e}"}

    async def run_install_fgmod(self, selected_default_variant: str = bundle.DEFAULT_FSR4_VARIANT) -> dict:
        try:
            decky.logger.info("Starting OptiScaler installation from static bundle")
            selected_default_variant = bundle.normalize_variant(selected_default_variant)

            extract_result = await self.extract_static_optiscaler(selected_default_variant)
            if extract_result["status"] != "success":
                return {
                    "status": "error",
                    "message": f"OptiScaler extraction failed: {extract_result.get('message', 'Unknown error')}"
                }

            return {
                "status": "success",
                "output": (
                    "Successfully installed OptiScaler "
                    f"{extract_result.get('version', bundle.OPTISCALER_ARCHIVE_ASSET['version'])} "
                    f"with {extract_result.get('selected_default_variant_label', bundle.FSR4_VARIANTS[selected_default_variant]['label'])}."
                ),
                "version": extract_result.get("version", bundle.OPTISCALER_ARCHIVE_ASSET["version"]),
                "selected_default_variant": extract_result.get("selected_default_variant", selected_default_variant),
                "selected_default_variant_label": extract_result.get(
                    "selected_default_variant_label",
                    bundle.FSR4_VARIANTS[selected_default_variant]["label"],
                ),
            }

        except Exception as e:
            decky.logger.error(f"Unexpected error during installation: {str(e)}")
            return {
                "status": "error",
                "message": f"Installation failed: {str(e)}"
            }

    async def check_fgmod_path(self) -> dict:
        path = Path(decky.HOME) / "fgmod"
        required_files = [
            "OptiScaler.dll",
            "OptiScaler.ini",
            "dlssg_to_fsr3_amd_is_better.dll",
            "fakenvapi.dll",
            "fakenvapi.ini",
            "amd_fidelityfx_dx12.dll",
            "amd_fidelityfx_framegeneration_dx12.dll",
            bundle.FSR4_UPSCALER_FILENAME,
            "amd_fidelityfx_vk.dll",
            "libxess.dll",
            "libxess_dx11.dll",
            "libxess_fg.dll",
            "libxell.dll",
            "fgmod",
            "fgmod-uninstaller.sh",
            "update-optiscaler-config.py",
            bundle.INSTALL_MANIFEST_FILENAME,
        ]

        if not path.exists():
            return {"exists": False}

        for file_name in required_files:
            if not path.joinpath(file_name).exists():
                return {"exists": False}

        plugins_dir = path / "plugins"
        if not plugins_dir.exists() or not (plugins_dir / "OptiPatcher.asi").exists():
            return {"exists": False}

        for variant_id, variant in bundle.FSR4_VARIANTS.items():
            variant_dir = path / variant["dir_name"]
            variant_path = variant_dir / bundle.FSR4_UPSCALER_FILENAME
            if not variant_path.exists():
                return {"exists": False}
            injector = variant.get("injector")
            if isinstance(injector, dict):
                if not (variant_dir / injector.get("name", "OptiScaler.dll")).exists():
                    return {"exists": False}
                if not (variant_dir / "renames" / "dxgi.dll").exists():
                    return {"exists": False}
            for extra_file in variant.get("extra_files", []):
                if not (variant_dir / extra_file["name"]).exists():
                    return {"exists": False}

        manifest = bundle_store.load_manifest(path)
        selected_variant = bundle_store.selected_variant(path)
        return {
            "exists": True,
            "version": bundle_store.optiscaler_version(path),
            "selected_fsr4_variant": selected_variant,
            "selected_fsr4_variant_label": bundle.FSR4_VARIANTS[selected_variant]["label"],
            "install_manifest_present": bool(manifest),
        }




    # ── Steam library discovery ───────────────────────────────────────────────

    def _home_path(self) -> Path:
        try:
            return Path(decky.HOME)
        except TypeError:
            return Path(str(decky.HOME))






    # ── Patch target auto-detection ───────────────────────────────────────────








    # ── Marker file tracking ──────────────────────────────────────────────────




    # ── Launch options helpers ────────────────────────────────────────────────




    async def get_path_defaults(self) -> dict:
        try:
            home_path = Path(decky.HOME)
        except TypeError:
            home_path = Path(str(decky.HOME))

        steam_common = home_path / ".local" / "share" / "Steam" / "steamapps" / "common"

        return {
            "home": str(home_path),
            "steam_common": str(steam_common),
        }

    async def log_error(self, error: str) -> None:
        decky.logger.error(f"FRONTEND: {error}")



    # ── AppID-based patch / unpatch / status ───────────────────────────────────────

    # ── Game patching (delegated to the Patcher) ──────────────────────────────

    def _patcher(self) -> Patcher:
        return Patcher(self._home_path())

    async def list_installed_games(self) -> dict:
        return self._patcher().list_games()

    async def manual_patch_directory(
        self,
        directory: str,
        dll_name: str = "dxgi.dll",
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
        dll_name: str = "dxgi.dll",
        current_launch_options: str = "",
        fsr4_variant: str = bundle.DEFAULT_FSR4_VARIANT,
    ) -> dict:
        return self._patcher().patch_game(appid, dll_name, current_launch_options, fsr4_variant)

    async def unpatch_game(self, appid: str) -> dict:
        return self._patcher().unpatch_game(appid)
