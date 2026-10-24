"""Unpacking archives with the plugin's 7-Zip (a stand-in that speaks its command line)."""

import zipfile

import pytest

from conftest import FAKE_7Z, install_tools, write
from deckyscaler.infrastructure import archive


@pytest.fixture
def seven_zip(tmp_path):
    return install_tools(tmp_path / "plugin" / "tools", {"7zzs": FAKE_7Z}) / "7zzs"


@pytest.fixture
def archive_file(tmp_path):
    path = tmp_path / "OptiScaler.7z"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("OptiScaler.dll", b"opti")
        zf.writestr("OptiScaler/libxess.dll", b"xess")
    return path


def test_extract_7z_unpacks_into_a_new_directory(seven_zip, archive_file, tmp_path):
    out = tmp_path / "out" / "nested"

    archive.extract_7z(seven_zip, archive_file, out)

    assert (out / "OptiScaler" / "libxess.dll").read_bytes() == b"xess"


def test_extract_7z_reports_the_tools_error(seven_zip, tmp_path):
    broken = write(tmp_path / "broken.7z", b"not an archive")

    with pytest.raises(RuntimeError, match="BadZipFile|not a zip file"):
        archive.extract_7z(seven_zip, broken, tmp_path / "out")


def test_extract_7z_restores_the_exec_bit_decky_drops(seven_zip, archive_file, tmp_path):
    seven_zip.chmod(0o644)

    archive.extract_7z(seven_zip, archive_file, tmp_path / "out")

    assert (tmp_path / "out" / "OptiScaler.dll").exists()
    assert seven_zip.stat().st_mode & 0o100


def test_extract_7z_says_when_the_build_carries_no_7zip(tmp_path):
    with pytest.raises(RuntimeError, match="7-Zip is missing from this plugin build"):
        archive.extract_7z(tmp_path / "tools" / "7zzs", tmp_path / "a.7z", tmp_path / "out")
