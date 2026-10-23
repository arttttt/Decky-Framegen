"""Checks on the built plugin zip, as Decky Loader would install it.

CI builds the zip with Decky CLI and points PLUGIN_ZIP at it; without the
variable these tests are skipped.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_ZIP = os.environ.get("PLUGIN_ZIP")

pytestmark = pytest.mark.skipif(not PLUGIN_ZIP, reason="set PLUGIN_ZIP to a zip built by `decky plugin build`")


def repo_files(directory: str) -> set[str]:
    """Files under a repo directory, relative to that directory."""
    root = REPO_ROOT / directory
    if not root.exists():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }


@pytest.fixture(scope="module")
def plugin_root(tmp_path_factory) -> Path:
    """The zip unpacked; it holds a single directory named after the plugin."""
    out = tmp_path_factory.mktemp("package")
    with zipfile.ZipFile(PLUGIN_ZIP) as zf:
        zf.extractall(out)
    roots = [path for path in out.iterdir() if path.is_dir()]
    assert len(roots) == 1, f"expected one plugin directory, got {roots}"
    return roots[0]


def test_the_package_is_named_after_the_plugin_and_holds_its_entry_points(plugin_root):
    assert plugin_root.name == json.loads((REPO_ROOT / "plugin.json").read_text())["name"]
    for name in ("main.py", "plugin.json", "package.json", "LICENSE", "README.md", "dist/index.js"):
        assert (plugin_root / name).is_file(), f"{name} missing from the package"


def test_every_backend_module_is_shipped(plugin_root):
    shipped_root = plugin_root / "py_modules"
    shipped = {path.relative_to(shipped_root).as_posix() for path in shipped_root.rglob("*") if path.is_file()}

    assert repo_files("py_modules") <= shipped


def test_defaults_are_installed_at_the_plugin_root(plugin_root):
    # The backend reads its launcher scripts and licenses from <plugin>/assets.
    missing = {name for name in repo_files("defaults") if not (plugin_root / name).is_file()}

    assert not missing, f"defaults not at the plugin root: {sorted(missing)}"


def test_bundled_binaries_match_their_pinned_hashes(plugin_root):
    package_json = json.loads((REPO_ROOT / "package.json").read_text())
    for binary in package_json.get("remote_binary", []):
        path = plugin_root / "bin" / binary["name"]
        assert path.is_file(), f"bin/{binary['name']} missing"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binary["sha256hash"], f"bin/{binary['name']} hash"


# Runs in an isolated interpreter (-I) so nothing from the repository can be imported:
# only what the package ships.
IMPORT_SMOKE = """
import asyncio, logging, sys, tempfile, types
root = sys.argv[1]
decky = types.ModuleType("decky")
decky.HOME = tempfile.mkdtemp()
decky.DECKY_PLUGIN_DIR = root
decky.logger = logging.getLogger("decky")
sys.modules["decky"] = decky
sys.path[:0] = [root + "/py_modules", root]
import main
assert main.__file__.startswith(root), main.__file__
print(asyncio.run(main.Plugin().check_fgmod_path()))
"""


def test_the_backend_loads_from_the_package_alone_and_answers(plugin_root):
    result = subprocess.run(
        [sys.executable, "-I", "-c", IMPORT_SMOKE, str(plugin_root)], capture_output=True, text=True, cwd=plugin_root
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "{'exists': False}"
