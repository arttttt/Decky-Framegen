"""Test harness for the Python backend.

`main.py` imports `decky`, which only exists inside Decky Loader. A stand-in
module is registered before `main` is imported; each test then points its
paths at a private temporary directory.

The fixtures build a fake world on disk: an installed `~/fgmod` bundle, game
directories and a Steam library. Bundle files are small placeholder blobs —
the plugin tells its own files apart from foreign ones by content and hash,
so size does not matter. Variant hashes in `main.FSR4_VARIANTS` are swapped
for the hashes of those blobs so variant detection behaves as on a device.
"""

from __future__ import annotations

import copy
import hashlib
import json
import logging
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_decky = types.ModuleType("decky")
_decky.HOME = ""
_decky.DECKY_PLUGIN_DIR = ""
_decky.logger = logging.getLogger("decky")
sys.modules["decky"] = _decky
sys.path.insert(0, str(REPO_ROOT))

import main  # noqa: E402


# sha256 → label of every placeholder handed out, so snapshots can name content.
KNOWN_CONTENT: dict[str, str] = {}


def _labelled(label: str, data: bytes) -> bytes:
    KNOWN_CONTENT[hashlib.sha256(data).hexdigest()] = label
    return data


def blob(name: str) -> bytes:
    """Deterministic, unique placeholder content for a bundle file."""
    return _labelled(f"bundle:{name}", f"decky-framegen test blob: {name}\n".encode())


def game_file(name: str) -> bytes:
    """Deterministic content for a file the game itself ships."""
    return _labelled(f"game:{name}", f"file shipped by the game: {name}\n".encode())


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def snapshot(root: Path) -> dict[str, str | None]:
    """Map every file to its sha256 and every directory to None, keyed by relative path."""
    state: dict[str, str | None] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        state[rel] = None if path.is_dir() else sha256(path.read_bytes())
    return state


# Blob names for files whose content must be shared or told apart.
NATIVE_UPSCALER = "native amd_fidelityfx_upscaler_dx12.dll"
INT8_UPSCALER = "int8 amd_fidelityfx_upscaler_dx12.dll"
PRE10_INJECTOR = "pre10 OptiScaler.dll"
EXTRA_FILE_BLOBS = {
    ("rdna34-official-411", "amdxcffx64.dll"): "official amdxcffx64.dll",
    ("rdna2-valve-411-pre10", "amdxcffx64.dll"): "valve amdxcffx64.dll",
    ("rdna2-valve-411-pre10", "amdxc64.dll"): "valve amdxc64.dll",
}


@pytest.fixture
def fake_variants(monkeypatch) -> dict:
    """FSR4_VARIANTS with hashes rewritten to match the placeholder blobs."""
    variants = copy.deepcopy(main.FSR4_VARIANTS)
    for variant_id, variant in variants.items():
        upscaler = NATIVE_UPSCALER if variant["uses_archive_native"] else INT8_UPSCALER
        variant["sha256"] = sha256(blob(upscaler))
        for extra in variant.get("extra_files", []):
            extra["sha256"] = sha256(blob(EXTRA_FILE_BLOBS[(variant_id, extra["name"])]))
        if variant.get("injector"):
            variant["injector"]["sha256"] = sha256(blob(PRE10_INJECTOR))
    monkeypatch.setattr(main, "FSR4_VARIANTS", variants)
    return variants


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """A private home directory wired into the fake `decky` module."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(_decky, "HOME", str(home_dir))
    monkeypatch.setattr(_decky, "DECKY_PLUGIN_DIR", str(tmp_path / "plugin"))
    return home_dir


@pytest.fixture
def plugin(home) -> main.Plugin:
    return main.Plugin()


@pytest.fixture
def fgmod(home, fake_variants) -> Path:
    """An installed `~/fgmod` bundle, laid out as `extract_static_optiscaler` leaves it.

    The default variant (`rdna23-int8`) is active and has no extra files.
    """
    root = home / "fgmod"
    write(root / "OptiScaler.dll", blob("OptiScaler.dll"))
    write(root / "OptiScaler.ini", b"[FrameGen]\nFGInput=nukems\nFGOutput=nukems\n")
    for name in main.PROXY_DLL_BACKUPS:
        write(root / "renames" / name, blob("OptiScaler.dll"))
    for name in main.SUPPORT_FILES:
        write(root / name, blob(name))
    write(root / "D3D12_Optiscaler" / "D3D12Core.dll", blob("D3D12Core.dll"))
    write(root / "plugins" / "OptiPatcher.asi", blob("OptiPatcher.asi"))
    for name in ("fgmod", "fgmod-uninstaller.sh", "update-optiscaler-config.py"):
        write(root / name, blob(name))

    for variant_id, variant in fake_variants.items():
        variant_dir = root / variant["dir_name"]
        upscaler = NATIVE_UPSCALER if variant["uses_archive_native"] else INT8_UPSCALER
        write(variant_dir / main.FSR4_UPSCALER_FILENAME, blob(upscaler))
        for extra in variant.get("extra_files", []):
            write(variant_dir / extra["name"], blob(EXTRA_FILE_BLOBS[(variant_id, extra["name"])]))
        if variant.get("injector"):
            write(variant_dir / variant["injector"]["name"], blob(PRE10_INJECTOR))
            for name in main.PROXY_DLL_BACKUPS:
                write(variant_dir / "renames" / name, blob(PRE10_INJECTOR))

    write(root / main.FSR4_UPSCALER_FILENAME, blob(INT8_UPSCALER))
    manifest = {
        "schema_version": 1,
        "optiscaler": {"version": "test-0.9.4"},
        "selected_default_variant": main.DEFAULT_FSR4_VARIANT,
    }
    write(root / main.INSTALL_MANIFEST_FILENAME, json.dumps(manifest).encode())
    return root


def make_game_dir(path: Path, files: dict[str, bytes] | None = None) -> Path:
    """A game directory holding an executable plus any game-shipped files given."""
    write(path / "Game.exe", game_file("Game.exe"))
    for rel, data in (files or {}).items():
        write(path / rel, data)
    return path


@pytest.fixture
def game_dir(tmp_path) -> Path:
    """A clean game directory with nothing but its executable."""
    return make_game_dir(tmp_path / "games" / "Clean Game")


@dataclass
class SteamLibrary:
    """A Steam install under the fake home; `add_game` registers an installed title."""

    steamapps: Path
    games: dict[str, Path] = field(default_factory=dict)

    def add_game(self, appid: str, name: str, files: dict[str, bytes] | None = None) -> Path:
        install_dir = name.replace(" ", "")
        manifest = (
            '"AppState"\n{\n'
            f'\t"appid"\t\t"{appid}"\n'
            f'\t"name"\t\t"{name}"\n'
            f'\t"installdir"\t\t"{install_dir}"\n'
            "}\n"
        )
        write(self.steamapps / f"appmanifest_{appid}.acf", manifest.encode())
        game_root = make_game_dir(self.steamapps / "common" / install_dir, files)
        self.games[appid] = game_root
        return game_root


@pytest.fixture
def steam_library(home) -> SteamLibrary:
    steamapps = home / ".local" / "share" / "Steam" / "steamapps"
    steamapps.mkdir(parents=True)
    return SteamLibrary(steamapps=steamapps)
