"""Test harness for the Python backend.

`main.py` imports `decky`, which only exists inside Decky Loader. A stand-in
module is registered before `main` is imported; each test then points its
paths at a private temporary directory.

The fixtures build a fake world on disk: a `~/fgmod` with an OptiScaler library
(a 0.9 stable version as the default and a 10 nightly one, laid out as their real
archives are), game directories and a Steam library. Version files are small
placeholder blobs — the plugin records and compares them by hash, so size does
not matter.
"""

from __future__ import annotations

import asyncio
import hashlib
import http.server
import json
import logging
import os
import shutil
import sys
import threading
import types
from dataclasses import dataclass, field
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

_decky = types.ModuleType("decky")
_decky.HOME = ""
_decky.DECKY_PLUGIN_DIR = ""
_decky.DECKY_PLUGIN_RUNTIME_DIR = ""
_decky.logger = logging.getLogger("decky")
sys.modules["decky"] = _decky
# Decky puts the plugin's py_modules on sys.path; the repo root holds main.py.
sys.path[:0] = [str(REPO_ROOT / "py_modules"), str(REPO_ROOT)]

import main  # noqa: E402
from framegen.domain import bundle  # noqa: E402


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


def run(coro):
    """Run one of the plugin's async methods to completion."""
    return asyncio.run(coro)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def install_tools(directory: Path, scripts: dict[str, str]) -> Path:
    """Executable stand-ins for command-line tools, written into `directory`."""
    for name, body in scripts.items():
        write(directory / name, body.encode()).chmod(0o755)
    return directory


def put_tools_on_path(monkeypatch, directory: Path, scripts: dict[str, str]) -> Path:
    """Stand-in tools that shadow the real ones for the rest of the test."""
    install_tools(directory, scripts)
    monkeypatch.setenv("PATH", f"{directory}{os.pathsep}{os.environ['PATH']}")
    return directory


def snapshot(root: Path) -> dict[str, str | None]:
    """Map every file to its sha256 and every directory to None, keyed by relative path."""
    state: dict[str, str | None] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        state[rel] = None if path.is_dir() else sha256(path.read_bytes())
    return state


@pytest.fixture
def home(tmp_path, monkeypatch) -> Path:
    """A private home directory wired into the fake `decky` module."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    monkeypatch.setattr(_decky, "HOME", str(home_dir))
    monkeypatch.setattr(_decky, "DECKY_PLUGIN_DIR", str(tmp_path / "plugin"))
    monkeypatch.setattr(_decky, "DECKY_PLUGIN_RUNTIME_DIR", str(tmp_path / "runtime"))
    return home_dir


@pytest.fixture
def plugin(home) -> main.Plugin:
    return main.Plugin()


# The files of library versions, as their real archives lay them out (blob labels name the source).
STABLE_FILES = {
    "OptiScaler.dll": "OptiScaler.dll",
    "OptiScaler.ini": None,
    "amd_fidelityfx_dx12.dll": "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_upscaler_dx12.dll": "amd_fidelityfx_upscaler_dx12.dll",
    "dlssg_to_fsr3_amd_is_better.dll": "dlssg_to_fsr3_amd_is_better.dll",
    "fakenvapi.dll": "fakenvapi.dll",
    "fakenvapi.ini": "fakenvapi.ini",
    "libxess.dll": "libxess.dll",
    "libxess_dx11.dll": "libxess_dx11.dll",
    "D3D12_Optiscaler/D3D12Core.dll": "D3D12Core.dll",
    "Licenses/XeSS_LICENSE.txt": "XeSS_LICENSE.txt",
    "!!.txt": "readme",
    "setup_linux.sh": "setup_linux.sh",
}
NIGHTLY_FILES = {
    "OptiScaler.dll": "v10 OptiScaler.dll",
    "OptiScaler.ini": None,
    "OptiScaler/amd_fidelityfx_upscaler_dx12.dll": "v10 amd_fidelityfx_upscaler_dx12.dll",
    "OptiScaler/libxess.dll": "v10 libxess.dll",
    "OptiScaler/D3D12_OptiScaler/D3D12Core.dll": "v10 D3D12Core.dll",
    "OptiScaler/Streamlined_fetcher_windows.bat": "fetcher",
    "setup_windows.bat": "setup_windows.bat",
}
STABLE_INI = "[FrameGen]\nFGInput=auto\nFGOutput=auto\n\n[FSR]\nFsr4Update=auto\nFsr4ForceEnableInt8=auto\n\n[Menu]\nUseHQFont=auto\n"
NIGHTLY_INI = "[FrameGen]\nFGInput=auto\n\n[FSR]\nFsr4GpuSupport=auto\nFsr4Model=auto\n\n[Menu]\nUseHQFont=auto\n"
STABLE, NIGHTLY = "stable-0.9.4", "nightly-20261023"


def install_version(fgmod: Path, version_id: str, family: str, files: dict[str, str | None], ini: str) -> Path:
    """A version in ~/fgmod/library as the library service leaves it."""
    from framegen.domain import library

    root = fgmod / "library" / "versions" / version_id
    for rel, label in files.items():
        write(root / "files" / rel, ini.encode() if label is None else blob(label))
    channel, _, rest = version_id.partition("-")
    entry = library.Installed(version_id, channel, rest if channel == "stable" else "10.0.0-pre1",
                              "20260718" if channel == "stable" else rest, family, "https://x", "0" * 64, "2026-10-24")
    write(root / "entry.json", json.dumps(library.entry_json(entry)).encode())
    return root


@pytest.fixture
def fgmod(home) -> Path:
    """~/fgmod with the plugin's core and launch scripts, and a library holding OptiScaler 0.9.4
    (the default) and a v10 nightly."""
    root = home / "fgmod"
    shutil.copytree(
        REPO_ROOT / "py_modules" / bundle.CORE_PACKAGE,
        root / bundle.CORE_PACKAGE,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    for name in ("fgmod", "fgmod-uninstaller.sh", "update-optiscaler-config.py"):
        write(root / name, blob(name))
    install_version(root, STABLE, "0.9", STABLE_FILES, STABLE_INI)
    install_version(root, NIGHTLY, "10", NIGHTLY_FILES, NIGHTLY_INI)
    write(root / "library" / "settings.json", json.dumps({"default_version": STABLE}).encode())
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


# ── 7-Zip ────────────────────────────────────────────────────────────────────

FAKE_7Z = f"""#!{sys.executable}
import sys, zipfile
args = sys.argv[1:]
assert args[:2] == ["x", "-y"], args
out_dir = args[2][len("-o"):]
archive, members = args[3], args[4:]
with zipfile.ZipFile(archive) as zf:
    zf.extractall(out_dir, members or None)
"""
"""A stand-in for tools/7zzs: it unpacks zips with 7-Zip's command line."""


# ── GitHub ───────────────────────────────────────────────────────────────────


@pytest.fixture
def github_api(monkeypatch):
    """A local stand-in for api.github.com: every GET answers `.status` and `.body` (a JSON list by default)."""
    from framegen.infrastructure import github_releases

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            server.requests.append(self.path)
            self.send_response(server.status)
            self.end_headers()
            self.wfile.write(server.body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.status, server.body, server.requests = 200, b"[]", []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(github_releases, "API_ROOT", f"http://127.0.0.1:{server.server_port}")
    yield server
    server.shutdown()
    server.server_close()
