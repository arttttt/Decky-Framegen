"""Installing, switching and removing the shared OptiScaler bundle in ~/fgmod."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

from framegen.domain import bundle, ini
from framegen.infrastructure import archive, bundle_store, files, game_directory

log = logging.getLogger(__name__)

# The framegen package this module belongs to.
CORE_SOURCE = Path(__file__).resolve().parents[1]


class AssetError(RuntimeError):
    """A bundled asset is missing or does not match its expected hash."""


def _verified(path: Path, expected_sha256: str, description: str) -> str:
    actual = files.sha256(path)
    if actual.lower() != expected_sha256.lower():
        raise AssetError(f"{description} hash mismatch: expected {expected_sha256}, got {actual}")
    return actual


def _copy_verified(source: Path, destination: Path, expected_sha256: str, description: str) -> str:
    shutil.copy2(source, destination)
    return _verified(destination, expected_sha256, description)


class Installer:
    def __init__(self, home: Path, plugin_dir: Path):
        self.fgmod_path = home / "fgmod"
        self.bin_path = plugin_dir / "bin"
        self.assets_path = plugin_dir / "assets"

    # ── install ──────────────────────────────────────────────────────────────

    def install(self, selected_variant: str) -> dict:
        variant = bundle.normalize_variant(selected_variant)
        log.info("Starting OptiScaler installation from static bundle")
        if not self.bin_path.exists():
            return {"status": "error", "message": "This plugin build does not include OptiScaler."}
        try:
            extracted = self._extract(variant)
        except Exception as exc:
            log.error(f"Unexpected error during installation: {exc}")
            return {"status": "error", "message": f"Installation failed: {exc}"}
        if extracted["status"] != "success":
            return {
                "status": "error",
                "message": f"OptiScaler extraction failed: {extracted.get('message', 'Unknown error')}",
            }
        return {
            "status": "success",
            "output": (
                f"Successfully installed OptiScaler {extracted['version']} "
                f"with {extracted['selected_default_variant_label']}."
            ),
            "version": extracted["version"],
            "selected_default_variant": extracted["selected_default_variant"],
            "selected_default_variant_label": extracted["selected_default_variant_label"],
        }

    def _extract(self, variant: str) -> dict:
        """Prepare ~/fgmod with every bundled FSR4 runtime variant and activate `variant`."""
        try:
            for asset in bundle.RELEASE_ASSETS:
                source = self.bin_path / asset["name"]
                if not source.exists():
                    return {"status": "error", "message": f"Required bundled asset missing: {asset['name']}"}
                _verified(source, asset["sha256"], asset["name"])

            fgmod = self.fgmod_path
            if fgmod.exists():
                shutil.rmtree(fgmod)
            fgmod.mkdir(parents=True, exist_ok=True)
            archive.extract_7z(self.bin_path / bundle.OPTISCALER_ARCHIVE_ASSET["name"], fgmod)

            self._create_renamed_copies(fgmod / "OptiScaler.dll", fgmod / "renames")
            self._install_launcher_scripts()
            shutil.copytree(
                CORE_SOURCE, fgmod / bundle.CORE_PACKAGE, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
            )
            optipatcher_sha256 = _copy_verified(
                self.bin_path / bundle.OPTIPATCHER_ASSET["name"],
                self._mkdir_parent(fgmod / bundle.OPTIPATCHER_TARGET),
                bundle.OPTIPATCHER_ASSET["sha256"],
                "Prepared OptiPatcher plugin",
            )
            game_directory.edit_ini(fgmod / "OptiScaler.ini", ini.apply_bundle_defaults, "apply plugin defaults")

            native_upscaler = fgmod / bundle.FSR4_UPSCALER_FILENAME
            native_upscaler_sha256 = _verified(
                native_upscaler, bundle.FSR4_VARIANTS["rdna4-native"]["sha256"], "Archive-native FSR4 upscaler"
            )
            for variant_id in bundle.FSR4_VARIANTS:
                self._prepare_variant(variant_id, native_upscaler)

            variant = self._activate(variant)
            (fgmod / bundle.VERSION_FILENAME).write_text(bundle.OPTISCALER_ARCHIVE_ASSET["version"], encoding="utf-8")
            files.write_json(
                bundle_store.manifest_path(fgmod),
                bundle.install_manifest(
                    selected_variant=variant,
                    native_upscaler_sha256=native_upscaler_sha256,
                    optipatcher_sha256=optipatcher_sha256,
                    active_upscaler_sha256=files.sha256(fgmod / bundle.FSR4_UPSCALER_FILENAME),
                    installed_at=datetime.now(timezone.utc).isoformat(),
                ),
            )
        except Exception as exc:
            log.exception(f"Extract failed with exception: {exc}")
            return {"status": "error", "message": f"Extract failed: {exc}"}

        version = bundle.OPTISCALER_ARCHIVE_ASSET["version"]
        return {
            "status": "success",
            "message": f"Successfully extracted OptiScaler {version} to ~/fgmod",
            "version": version,
            "selected_default_variant": variant,
            "selected_default_variant_label": bundle.FSR4_VARIANTS[variant]["label"],
        }

    @staticmethod
    def _mkdir_parent(path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _create_renamed_copies(source: Path, renames_dir: Path) -> None:
        """The OptiScaler injector under every proxy name a game can load it as."""
        if not source.exists():
            raise AssetError(f"Failed to prepare renamed OptiScaler proxies: {source} does not exist")
        renames_dir.mkdir(exist_ok=True)
        for name in bundle.PROXY_DLL_BACKUPS:
            shutil.copy2(source, renames_dir / name)

    def _install_launcher_scripts(self) -> None:
        for installed_name, source_name in bundle.LAUNCHER_SCRIPTS.items():
            source = self.assets_path / source_name
            if source.exists():
                destination = self.fgmod_path / installed_name
                shutil.copy2(source, destination)
                destination.chmod(0o755)

    def _prepare_variant(self, variant_id: str, native_upscaler: Path) -> None:
        """Lay out one variant's directory: its upscaler, extra driver DLLs and own injector."""
        variant = bundle.FSR4_VARIANTS[variant_id]
        variant_dir = bundle.variant_dir(self.fgmod_path, variant_id)
        variant_dir.mkdir(parents=True, exist_ok=True)
        upscaler_source = native_upscaler if variant["uses_archive_native"] else self.bin_path / variant["source_asset_name"]
        _copy_verified(
            upscaler_source,
            variant_dir / bundle.FSR4_UPSCALER_FILENAME,
            variant["sha256"],
            f"Prepared {variant_id} FSR4 upscaler",
        )
        for extra in variant.get("extra_files", []):
            _copy_verified(
                self.bin_path / extra["source_asset_name"],
                variant_dir / extra["name"],
                extra["sha256"],
                f"Prepared {variant_id} {extra['name']}",
            )
        injector = bundle.variant_injector(variant_id)
        if injector:
            injector_path = variant_dir / injector["name"]
            _copy_verified(
                self.bin_path / injector["source_asset_name"],
                injector_path,
                injector["sha256"],
                f"Prepared {variant_id} OptiScaler injector",
            )
            self._create_renamed_copies(injector_path, variant_dir / "renames")

    # ── default variant ──────────────────────────────────────────────────────

    def _activate(self, variant: str) -> str:
        """Make `variant` the bundle's active root upscaler and extra files."""
        variant = bundle.normalize_variant(variant)
        upscaler = bundle.variant_upscaler_path(self.fgmod_path, variant)
        if not upscaler.exists():
            raise FileNotFoundError(f"Prepared FSR4 variant missing: {upscaler}")
        shutil.copy2(upscaler, self.fgmod_path / bundle.FSR4_UPSCALER_FILENAME)
        selected_extras = {extra["name"] for extra in bundle.variant_extra_files(variant)}
        for filename in bundle.VARIANT_EXTRA_FILENAMES:
            root_copy = self.fgmod_path / filename
            if filename not in selected_extras:
                root_copy.unlink(missing_ok=True)
                continue
            source = bundle.variant_extra_file_path(self.fgmod_path, variant, filename)
            if not source.exists():
                raise FileNotFoundError(f"Prepared FSR4 variant extra file missing: {source}")
            shutil.copy2(source, root_copy)
        return variant

    def switch_default(self, selected_variant: str) -> dict:
        try:
            if not self.fgmod_path.exists():
                return {"status": "error", "message": "OptiScaler bundle not installed. Run Install first."}
            manifest = bundle_store.load_manifest(self.fgmod_path)
            if not manifest:
                return {"status": "error", "message": "Install manifest missing. Reinstall OptiScaler."}
            variant = self._activate(selected_variant)
            manifest["selected_default_variant"] = variant
            manifest["active_root_upscaler"] = {
                "path": bundle.FSR4_UPSCALER_FILENAME,
                "sha256": files.sha256(self.fgmod_path / bundle.FSR4_UPSCALER_FILENAME),
                "variant": variant,
            }
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            files.write_json(bundle_store.manifest_path(self.fgmod_path), manifest)
        except Exception as exc:
            log.error(f"Failed to switch default FSR4 runtime: {exc}")
            return {"status": "error", "message": f"Failed to switch default FSR4 runtime: {exc}"}
        label = bundle.FSR4_VARIANTS[variant]["label"]
        return {
            "status": "success",
            "output": f"Default FSR4 runtime switched to {label}.",
            "version": bundle_store.optiscaler_version(self.fgmod_path),
            "selected_default_variant": variant,
            "selected_default_variant_label": label,
        }

    # ── uninstall and status ─────────────────────────────────────────────────

    def uninstall(self) -> dict:
        try:
            if not self.fgmod_path.exists():
                return {"status": "success", "output": "No fgmod directory found to remove"}
            shutil.rmtree(self.fgmod_path)
            log.info(f"Removed directory: {self.fgmod_path}")
            return {"status": "success", "output": "Successfully removed fgmod directory"}
        except Exception as exc:
            log.error(f"Uninstall error: {exc}")
            return {"status": "error", "message": f"Uninstall failed: {exc}", "output": str(exc)}

    def status(self) -> dict:
        fgmod = self.fgmod_path
        if not fgmod.exists() or not all((fgmod / path).exists() for path in bundle.required_install_paths()):
            return {"exists": False}
        variant = bundle_store.selected_variant(fgmod)
        return {
            "exists": True,
            "version": bundle_store.optiscaler_version(fgmod),
            "selected_fsr4_variant": variant,
            "selected_fsr4_variant_label": bundle.FSR4_VARIANTS[variant]["label"],
            "install_manifest_present": bool(bundle_store.load_manifest(fgmod)),
        }
