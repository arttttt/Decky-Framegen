"""Characterization tests for installing, switching and removing the ~/fgmod bundle.

The installer verifies bundled assets by sha256 and unpacks the OptiScaler
archive with the `7z` CLI. The tests stage placeholder assets whose hashes the
asset table is pointed at, and put a stand-in `7z` on PATH that understands the
one invocation the installer uses (`7z x -y -o<dir> <archive> [members]`) for a
zip file. Results are compared with golden files, like the patch scenarios.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import stat
import sys
import zipfile
from pathlib import Path

import pytest

from framegen import bundle
from conftest import INT8_UPSCALER, NATIVE_UPSCALER, PRE10_INJECTOR, REPO_ROOT, blob, sha256, write
from golden import assert_golden, describe_tree, normalize_result

FAKE_7Z = f"""#!{sys.executable}
import sys, zipfile
args = sys.argv[1:]
assert args[:2] == ["x", "-y"], args
out_dir = args[2][len("-o"):]
archive, members = args[3], args[4:]
with zipfile.ZipFile(archive) as zf:
    zf.extractall(out_dir, members or None)
"""

ARCHIVE_INI = (
    "[FrameGen]\nEnabled=auto\nFGInput=auto\nFGOutput=auto\n\n"
    "[FSR]\nFsr4Update=auto\n\n[Plugins]\nLoadAsiPlugins=auto\n\n[Menu]\nUseHQFont=auto\n"
)

# Bundled asset table entry → placeholder blob it is staged as.
ASSET_BLOBS = {
    "FSR4_INT8_ASSET": INT8_UPSCALER,
    "FSR4_OFFICIAL_411_ASSET": "official amdxcffx64.dll",
    "FSR4_VALVE_411_ASSET": "valve amdxcffx64.dll",
    "AMDXC64_RDNA2_ASSET": "valve amdxc64.dll",
    "OPTISCALER_PRE10_ASSET": PRE10_INJECTOR,
    "OPTIPATCHER_ASSET": "OptiPatcher.asi",
}


@pytest.fixture
def release_assets(home, fake_variants, tmp_path, monkeypatch) -> Path:
    """The plugin directory as Decky installs it: bin/ with every bundled asset, assets/ with scripts."""
    plugin_dir = tmp_path / "plugin"
    bin_dir = plugin_dir / "bin"

    archive = bin_dir / bundle.OPTISCALER_ARCHIVE_ASSET["name"]
    archive.parent.mkdir(parents=True)
    members = {
        "OptiScaler.dll": blob("OptiScaler.dll"),
        "OptiScaler.ini": ARCHIVE_INI.encode(),
        **{name: blob(name) for name in bundle.SUPPORT_FILES},
        bundle.FSR4_UPSCALER_FILENAME: blob(NATIVE_UPSCALER),
        "D3D12_Optiscaler/D3D12Core.dll": blob("D3D12Core.dll"),
    }
    with zipfile.ZipFile(archive, "w") as zf:
        for name, data in members.items():
            # A fixed timestamp keeps the archive, and so its hash, identical across runs.
            zf.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data)
    monkeypatch.setitem(bundle.OPTISCALER_ARCHIVE_ASSET, "sha256", sha256(archive.read_bytes()))

    for table_name, blob_name in ASSET_BLOBS.items():
        asset = getattr(bundle, table_name)
        write(bin_dir / asset["name"], blob(blob_name))
        monkeypatch.setitem(asset, "sha256", sha256(blob(blob_name)))

    shutil.copytree(REPO_ROOT / "defaults" / "assets", plugin_dir / "assets")

    tools = tmp_path / "tools"
    seven_zip = write(tools / "7z", FAKE_7Z.encode())
    seven_zip.chmod(seven_zip.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{tools}:{os.environ['PATH']}")
    return plugin_dir


def run(coro):
    return asyncio.run(coro)


@pytest.mark.parametrize("variant", sorted(bundle.FSR4_VARIANTS))
def test_install_bundle(variant, plugin, release_assets, home, tmp_path):
    result = run(plugin.run_install_fgmod(variant))

    assert_golden(
        f"install_{variant}",
        {
            "result": normalize_result(result, tmp_path),
            "check": run(plugin.check_fgmod_path()),
            "fgmod": describe_tree(home / "fgmod"),
        },
    )


def test_switch_default_variant(plugin, release_assets, home, tmp_path):
    run(plugin.run_install_fgmod("rdna23-int8"))
    steps = []
    for variant in ("rdna2-valve-411-pre10", "rdna34-official-411", "not-a-variant"):
        result = run(plugin.set_default_fsr4_variant(variant))
        fgmod = home / "fgmod"
        steps.append(
            {
                "switch to": variant,
                "result": normalize_result(result, tmp_path),
                "root files": {
                    name: describe_tree(fgmod).get(name)
                    for name in (bundle.FSR4_UPSCALER_FILENAME, *bundle.VARIANT_EXTRA_FILENAMES)
                },
                "manifest selection": json.loads(
                    (fgmod / bundle.INSTALL_MANIFEST_FILENAME).read_text()
                )["selected_default_variant"],
            }
        )

    assert_golden("switch_default_variant", steps)


def test_install_refuses_tampered_asset_and_keeps_existing_bundle(plugin, release_assets, home, tmp_path):
    run(plugin.run_install_fgmod("rdna23-int8"))
    before = describe_tree(home / "fgmod")
    write(release_assets / "bin" / bundle.FSR4_INT8_ASSET["name"], b"tampered")

    result = run(plugin.run_install_fgmod("rdna23-int8"))

    assert result["status"] == "error"
    assert "hash mismatch" in result["message"]
    assert describe_tree(home / "fgmod") == before


def test_install_reports_missing_bin_dir(plugin, home, tmp_path):
    result = run(plugin.run_install_fgmod("rdna23-int8"))

    assert normalize_result(result, tmp_path) == {
        "status": "error",
        "message": "OptiScaler extraction failed: Bin directory not found: <root>/plugin/bin",
    }


def test_uninstall_bundle(plugin, release_assets, home):
    run(plugin.run_install_fgmod("rdna23-int8"))

    first = run(plugin.run_uninstall_fgmod())
    second = run(plugin.run_uninstall_fgmod())

    assert first == {"status": "success", "output": "Successfully removed fgmod directory"}
    assert second == {"status": "success", "output": "No fgmod directory found to remove"}
    assert not (home / "fgmod").exists()
    assert run(plugin.check_fgmod_path()) == {"exists": False}
