"""The OptiScaler library: its rules on the device (unit) and the service against a fake GitHub and 7-Zip (integration)."""

from __future__ import annotations

import io
import json
import shutil
import zipfile
from pathlib import Path

import pytest

import main
from conftest import FAKE_7Z, REPO_ROOT, install_tools, run, sha256, write
from framegen.application.library import Library
from framegen.domain import library
from framegen.infrastructure import archive, github_releases

FIXTURES = Path(__file__).parent / "fixtures"
NEWEST = "nightly-20261023"

# ── unit: what the library section lists, and what may be removed ────────────


def installed_entry(version_id: str = NEWEST, channel: str = library.NIGHTLY, date: str = "20261023") -> library.Installed:
    return library.Installed(version_id, channel, "10.0.0-pre1", date, "10", "https://x", "0" * 64, "2026-10-24")


def test_installed_versions_stay_listed_even_when_upstream_no_longer_publishes_them():
    published = library.available(library.NIGHTLY, json.loads((FIXTURES / "optiscaler_nightly.json").read_text()))
    pruned = installed_entry("nightly-20260807", date="20260807")
    current = installed_entry()

    rows = library.catalog([current, pruned], published, NEWEST, {NEWEST: 100, "nightly-20260807": 50})

    assert rows[0] == library.Row(NEWEST, "10.0.0-pre1", "20261023", "10", library.INSTALLED, None, 100, True)
    assert [row.id for row in rows].count(NEWEST) == 1
    assert rows[-1].id == "nightly-20260807" and rows[-1].state == library.INSTALLED
    assert {row.state for row in rows[1:-1]} == {library.AVAILABLE}


@pytest.mark.parametrize(
    ("version_id", "installed", "default", "refusal"),
    [
        ("a", {"a", "b"}, "b", None),
        ("a", {"a", "b"}, "a", "This is the default version. Choose another default before removing it."),
        ("a", {"a"}, "a", None),  # the last version goes, default or not
        ("c", {"a"}, "a", "c is not in the library."),
    ],
)
def test_the_default_version_is_removed_only_when_it_is_the_last_one(version_id, installed, default, refusal):
    assert library.removal_refused(version_id, installed, default) == refusal


def test_an_entry_that_is_not_one_is_not_in_the_library():
    good = library.entry_json(installed_entry())

    assert library.parse_entry(good) == installed_entry()
    assert library.parse_entry({**good, "family": "0.7"}) is None
    assert library.parse_entry({**good, "channel": "beta"}) is None
    assert library.parse_entry({key: value for key, value in good.items() if key != "sha256"}) is None
    assert library.parse_entry([]) is None


# ── unit: what patching offers ──────────────────────────────────────────────


def test_patching_offers_installed_versions_newest_first():
    stable = library.Installed("stable-0.9.4", library.STABLE, "0.9.4", "20260718", "0.9", "u", "0" * 64, "t")
    nightly = installed_entry()

    offered = [library.choice_json(entry) for entry in library.newest_first([stable, nightly])]

    assert offered == [
        {"id": NEWEST, "version": "10.0.0-pre1", "channel": "nightly", "date": "20261023"},
        {"id": "stable-0.9.4", "version": "0.9.4", "channel": "stable", "date": "20260718"},
    ]


def test_a_newer_version_is_the_newest_later_build_of_the_same_channel():
    old, mid, new = (installed_entry(f"nightly-2026100{n}", date=f"2026100{n}") for n in (1, 2, 3))
    stable = library.Installed("stable-0.9.5", library.STABLE, "0.9.5", "20261231", "0.9", "u", "0" * 64, "t")
    installed = [mid, stable, new, old]

    assert library.newer_in_channel(installed, old.id) == new.id
    assert library.newer_in_channel(installed, new.id) is None  # a later stable is another channel
    assert library.newer_in_channel(installed, "nightly-20250101") is None  # not in the library any more
    assert library.newer_in_channel(installed, None) is None


# ── integration: the service ────────────────────────────────────────────────

V10_FILES = {
    "OptiScaler.dll": b"opti", "OptiScaler.ini": b"[FrameGen]\n",
    "OptiScaler/amd_fidelityfx_upscaler_dx12.dll": b"sdk", "OptiScaler/D3D12_OptiScaler/D3D12Core.dll": b"d3d",
}


def zip_archive(files: dict[str, bytes]) -> bytes:
    """What the stand-in 7zzs unpacks (it reads zips with 7-Zip's command line)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        for name, data in files.items():
            zf.writestr(zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)), data)
    return buffer.getvalue()


class FakeDownload:
    def __init__(self, content: bytes):
        self.content, self.urls = content, []

    def __call__(self, url, destination, on_progress):
        self.urls.append(url)
        destination.write_bytes(self.content)
        on_progress(len(self.content), len(self.content))


@pytest.fixture
def world(home, tmp_path, github_api):
    """~/fgmod, the plugin's tools/7zzs (a stand-in), and GitHub publishing the nightly listing
    with the newest build's digest and size matching `world.archive`."""

    class World:
        fgmod = home / "fgmod"
        seven_zip = install_tools(tmp_path / "plugin" / "tools", {"7zzs": FAKE_7Z}) / "7zzs"
        reports: list = []
        refreshes: list = []

        def publish(self, archive_bytes: bytes) -> None:
            listing = json.loads((FIXTURES / "optiscaler_nightly.json").read_text())
            listing[0]["assets"][0]["digest"] = f"sha256:{sha256(archive_bytes)}"
            listing[0]["assets"][0]["size"] = len(archive_bytes)
            github_api.body = json.dumps(listing).encode()
            self.archive = archive_bytes

        def library(self, download=None) -> Library:
            return Library(
                self.fgmod, self.seven_zip, github_releases.list_releases,
                download or FakeDownload(self.archive), lambda *args: self.reports.append(args),
                lambda: self.refreshes.append("core"),
            )

        def tree(self) -> list[str]:
            root = self.fgmod / "library"
            return sorted(p.relative_to(root).as_posix() for p in root.rglob("*")) if root.exists() else []

    world = World()
    world.publish(zip_archive(V10_FILES))
    return world


def test_installing_adds_the_unpacked_version_and_makes_the_first_one_default(world):
    result = world.library().install(library.NIGHTLY, NEWEST)

    assert result == {"status": "success", "id": NEWEST, "message": "OptiScaler 10.0.0-pre1 is installed."}
    files = world.fgmod / "library" / "versions" / NEWEST / "files"
    assert (files / "OptiScaler" / "amd_fidelityfx_upscaler_dx12.dll").read_bytes() == b"sdk"
    entry = json.loads((world.fgmod / "library" / "versions" / NEWEST / "entry.json").read_text())
    assert entry["id"] == NEWEST and entry["family"] == "10"
    assert not (world.fgmod / "library" / ".partial").exists()
    assert world.reports[-1] == (NEWEST, len(world.archive), len(world.archive))
    assert world.refreshes == ["core"]

    listed = world.library().versions(library.NIGHTLY)
    assert listed["versions"][0] | {"size": 0} == {
        "id": NEWEST, "version": "10.0.0-pre1", "date": "20261023", "family": "10",
        "state": "installed", "reason": None, "size": 0, "default": True,
    }
    assert listed["installed_bytes"] == sum(len(data) for data in V10_FILES.values()) + len(
        (world.fgmod / "library" / "versions" / NEWEST / "entry.json").read_bytes()
    )


def failing(world, case):
    if case == "checksum":
        return world.library(FakeDownload(b"not the published archive"))
    if case == "broken-archive":
        world.publish(b"not a zip, so the stand-in 7-Zip fails")
    if case == "missing-file":
        world.publish(zip_archive({k: v for k, v in V10_FILES.items() if k != "OptiScaler.ini"}))
    return world.library()


@pytest.mark.parametrize(
    ("case", "message"),
    [
        ("checksum", "did not match its checksum"),
        ("broken-archive", f"Installing {NEWEST} failed"),
        ("missing-file", "lacks OptiScaler.ini; not added"),
    ],
)
def test_a_failed_install_leaves_the_library_as_it_was(world, case, message):
    result = failing(world, case).install(library.NIGHTLY, NEWEST)

    assert result["status"] == "error"
    assert message in result["message"]
    assert world.tree() == []
    assert world.refreshes == []


def test_an_install_without_room_is_refused_before_downloading(world, monkeypatch):
    download = FakeDownload(world.archive)
    monkeypatch.setattr("framegen.infrastructure.library_store.LibraryStore.free_bytes", lambda self: 10)

    result = world.library(download).install(library.NIGHTLY, NEWEST)

    assert result["message"].startswith("Not enough free space")
    assert download.urls == []


@pytest.mark.parametrize(
    ("version_id", "message"),
    [("nightly-20260101", "is no longer published"), ("stable-0.9.4", "is no longer published")],
)
def test_only_a_version_the_channel_publishes_is_installed(world, version_id, message):
    assert message in world.library().install(library.NIGHTLY, version_id)["message"]


def test_installing_twice_is_refused_and_removing_follows_the_default_rule(world):
    first = world.library()
    first.install(library.NIGHTLY, NEWEST)

    assert "already in the library" in first.install(library.NIGHTLY, NEWEST)["message"]
    assert first.remove(NEWEST) == {"status": "success", "message": f"{NEWEST} is removed."}
    assert world.tree() == ["settings.json", "versions"]
    settings = json.loads((world.fgmod / "library" / "settings.json").read_text())
    assert settings["default_version"] is None
    assert first.set_default(NEWEST)["message"] == f"{NEWEST} is not in the library."


def test_a_library_directory_without_a_readable_entry_is_not_a_version(world):
    write(world.fgmod / "library" / "versions" / NEWEST / "files" / "OptiScaler.dll", b"leftover")

    rows = world.library().versions(library.NIGHTLY)["versions"]

    assert rows[0]["id"] == NEWEST and rows[0]["state"] == "available"


def test_github_failing_still_lists_what_is_installed(world, github_api):
    world.library().install(library.NIGHTLY, NEWEST)
    github_api.status, github_api.body = 403, b'{"message": "API rate limit exceeded"}'

    listed = world.library().versions(library.NIGHTLY)

    assert [row["id"] for row in listed["versions"]] == [NEWEST]
    assert listed["listing_error"].startswith("GitHub answered 403")


def test_the_plugin_installs_with_progress_events(plugin, world, tmp_path, monkeypatch):
    monkeypatch.setattr(github_releases, "download", FakeDownload(world.archive))
    events = []

    async def emit(event, *args):
        events.append((event, *args))

    monkeypatch.setattr(main.decky, "emit", emit, raising=False)
    assert (tmp_path / "plugin" / archive.SEVEN_ZIP).exists()  # the fake decky's DECKY_PLUGIN_DIR
    shutil.copytree(REPO_ROOT / "defaults" / "assets", tmp_path / "plugin" / "assets")

    result = run(plugin.library_install(library.NIGHTLY, NEWEST))

    assert result["status"] == "success"
    assert ("library_download", NEWEST, len(world.archive), len(world.archive)) in events
    # Installing also brings the plugin's core and launch scripts into ~/fgmod.
    assert (world.fgmod / "framegen" / "__main__.py").is_file()
    assert (world.fgmod / "fgmod").stat().st_mode & 0o100
    assert run(plugin.library_versions(library.NIGHTLY))["versions"][0]["state"] == "installed"


def test_a_version_listed_as_unsupported_is_never_downloaded(world, github_api):
    listing = json.loads(github_api.body)
    listing[0]["assets"][0].pop("digest")
    github_api.body = json.dumps(listing).encode()
    download = FakeDownload(world.archive)

    result = world.library(download).install(library.NIGHTLY, NEWEST)

    assert result["message"] == f"{NEWEST} can't be installed: {library.NO_CHECKSUM}."
    assert download.urls == []


def test_a_failed_core_refresh_does_not_turn_an_install_into_a_failure(world):
    def refresh():
        raise OSError("No space left on device")

    lib = world.library()
    lib.refresh_core = refresh

    result = lib.install(library.NIGHTLY, NEWEST)

    assert result["status"] == "success"
    assert result["message"].endswith("Updating the launch scripts in ~/fgmod failed: No space left on device")
    assert (world.fgmod / "library" / "versions" / NEWEST / "entry.json").exists()
    assert not (world.fgmod / "library" / "settings.json.new").exists()


def test_the_plugin_lists_what_games_can_be_patched_with(plugin, fgmod):
    from conftest import NIGHTLY, STABLE

    installed = run(plugin.library_installed())

    assert installed["default"] == STABLE
    assert [version["id"] for version in installed["versions"]] == [NIGHTLY, STABLE]
    write(fgmod / "library" / "settings.json", json.dumps({"default_version": "stable-0.9.1"}).encode())
    assert run(plugin.library_installed())["default"] is None  # a default no longer installed is none


def test_a_game_status_names_a_newer_version_of_its_channel(plugin, fgmod, steam_library):
    from conftest import NIGHTLY, NIGHTLY_FILES, NIGHTLY_INI, install_version

    steam_library.add_game("1234", "Test Game")
    run(plugin.patch_game("1234", "dxgi.dll", "", NIGHTLY))
    assert run(plugin.get_game_status("1234"))["newer_version"] is None

    install_version(fgmod, "nightly-20261101", "10", NIGHTLY_FILES, NIGHTLY_INI)

    assert run(plugin.get_game_status("1234"))["newer_version"] == "nightly-20261101"


def test_downloading_a_version_again_swaps_in_a_fresh_copy(world):
    world.library().install(library.NIGHTLY, NEWEST)
    files = world.fgmod / "library" / "versions" / NEWEST / "files"
    write(files / "OptiScaler.dll", b"corrupted")
    (files / "OptiScaler.ini").unlink()

    result = world.library().reinstall(NEWEST)

    assert result == {"status": "success", "id": NEWEST, "message": "OptiScaler 10.0.0-pre1 is downloaded again."}
    assert (files / "OptiScaler.dll").read_bytes() == b"opti"
    assert (files / "OptiScaler.ini").exists()
    assert not (world.fgmod / "library" / ".partial").exists()


def test_a_failed_download_again_keeps_the_copy_the_library_has(world):
    world.library().install(library.NIGHTLY, NEWEST)
    before = world.tree()

    result = world.library(FakeDownload(b"not the published archive")).reinstall(NEWEST)

    assert result["status"] == "error" and "did not match its checksum" in result["message"]
    assert world.tree() == before


def test_a_failed_swap_puts_the_old_copy_back(world, monkeypatch):
    world.library().install(library.NIGHTLY, NEWEST)
    before = world.tree()
    from framegen.infrastructure.library_store import LibraryStore

    def fail(self, stage, installed):
        raise OSError("disk full")

    monkeypatch.setattr(LibraryStore, "commit", fail)
    result = world.library().reinstall(NEWEST)

    assert result["status"] == "error" and "disk full" in result["message"]
    assert world.tree() == before


def test_only_a_version_in_the_library_is_downloaded_again(world):
    download = FakeDownload(world.archive)

    result = world.library(download).reinstall(NEWEST)

    assert result == {"status": "error", "message": f"{NEWEST} is not in the library."}
    assert download.urls == []
