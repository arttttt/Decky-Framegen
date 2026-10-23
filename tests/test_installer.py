"""Integration tests for the installer's pieces: unpacking archives and checking an install."""

import zipfile

import pytest

from conftest import sha256
from framegen.application.installer import Installer
from framegen.domain import bundle
from framegen.infrastructure import archive


def test_extract_7z_unpacks_into_a_new_directory(release_assets, tmp_path):
    out = tmp_path / "out" / "nested"

    archive.extract_7z(release_assets / archive.SEVEN_ZIP, release_assets / "bin" / bundle.OPTISCALER_ARCHIVE_ASSET["name"], out)

    assert (out / "OptiScaler.dll").exists()
    assert (out / "D3D12_Optiscaler" / "D3D12Core.dll").exists()


def test_extract_7z_reports_the_tools_error(release_assets, tmp_path):
    broken = tmp_path / "broken.7z"
    broken.write_bytes(b"not an archive")

    with pytest.raises(RuntimeError, match="BadZipFile|not a zip file"):
        archive.extract_7z(release_assets / archive.SEVEN_ZIP, broken, tmp_path / "out")


@pytest.mark.parametrize(
    "missing",
    ["OptiScaler.ini", "libxess.dll", "fgmod", "plugins/OptiPatcher.asi", "fsr4-rdna2-valve-411-pre10/amdxc64.dll",
     "fsr4-rdna2-valve-411-pre10/renames/dxgi.dll"],
)
def test_an_install_missing_any_required_file_is_reported_as_absent(missing, release_assets, home):
    installer = Installer(home, release_assets)
    assert installer.install("rdna23-int8")["status"] == "success"
    assert installer.status()["exists"] is True

    (home / "fgmod" / missing).unlink()

    assert installer.status() == {"exists": False}


def test_an_archive_without_the_upscaler_fails_the_install(release_assets, home, monkeypatch):
    archive_path = release_assets / "bin" / bundle.OPTISCALER_ARCHIVE_ASSET["name"]
    with zipfile.ZipFile(archive_path, "w"):
        pass  # valid but empty: the extracted bundle lacks the native upscaler
    monkeypatch.setitem(bundle.OPTISCALER_ARCHIVE_ASSET, "sha256", sha256(archive_path.read_bytes()))

    result = Installer(home, release_assets).install("rdna23-int8")

    assert result["status"] == "error"
    assert result["message"].startswith("OptiScaler extraction failed: Extract failed:")


def test_extract_7z_restores_the_exec_bit_decky_drops(release_assets, tmp_path):
    seven_zip = release_assets / archive.SEVEN_ZIP
    seven_zip.chmod(0o644)

    archive.extract_7z(seven_zip, release_assets / "bin" / bundle.OPTISCALER_ARCHIVE_ASSET["name"], tmp_path / "out")

    assert (tmp_path / "out" / "OptiScaler.dll").exists()
    assert seven_zip.stat().st_mode & 0o100


def test_extract_7z_says_when_the_build_carries_no_7zip(tmp_path):
    with pytest.raises(RuntimeError, match="7-Zip is missing from this plugin build"):
        archive.extract_7z(tmp_path / "tools" / "7zzs", tmp_path / "a.7z", tmp_path / "out")
