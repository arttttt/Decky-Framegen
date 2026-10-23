"""Characterization tests for installing, switching and removing the ~/fgmod bundle.

They run against the `release_assets` fixture (placeholder assets with matching
hashes and a stand-in `7z`), and compare results with golden files, like the
patch scenarios.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from conftest import write
from framegen.domain import bundle
from golden import assert_golden, describe_tree, normalize_result


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
