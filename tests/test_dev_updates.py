"""Other development builds: picking them from releases (unit) and listing them on the device (integration)."""

from __future__ import annotations

import copy
import hashlib
import http.server
import inspect
import json
import threading
from pathlib import Path

import pytest

import main
from conftest import run, write
from framegen.application.dev_updates import DevUpdates
from framegen.domain import dev_build
from framegen.infrastructure import github_releases

FIXTURE = Path(__file__).parent / "fixtures" / "github_releases.json"
REPOSITORY = "arttttt/Decky-Framegen"
PLUGIN = "Decky-Framegen"
DEV_COMMIT = "9f2c1a6bd4e8c7a5f3b2d1e0f6a5b4c3d2e1f0a9"
PR_COMMIT = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
RUNNING = dev_build.build_info(REPOSITORY, "dev", DEV_COMMIT)


def listing() -> list:
    return json.loads(FIXTURE.read_text())


def pr_12() -> dict:
    return copy.deepcopy(next(entry for entry in listing() if entry["tag_name"] == "pr-12"))


# ── unit: which releases are development builds ──────────────────────────────


def test_main_comes_first_then_pull_requests_newest_first_and_releases_are_left_out():
    found = dev_build.releases(listing(), RUNNING, PLUGIN)

    assert [release.info.channel for release in found] == ["dev", "pr-12", "pr-9"]


def test_a_release_carries_what_the_device_needs_to_show_and_install_it():
    release = dev_build.releases([pr_12()], RUNNING, PLUGIN)[0]

    assert release == dev_build.DevRelease(
        info=dev_build.build_info(REPOSITORY, "pr-12", PR_COMMIT),
        title="PR #12: Add a Developer section",
        published_at="2026-10-23T10:00:00Z",
        url="https://github.com/arttttt/Decky-Framegen/releases/download/pr-12/Decky-Framegen-1a2b3c4.zip",
        sha256="7e00ac50b658c754697f810ff3c91e881552081ddb7743b7f72ef500f1c5ca70",
    )


def _broken(change) -> dict:
    entry = pr_12()
    change(entry)
    return entry


@pytest.mark.parametrize(
    "entry",
    [
        _broken(lambda e: e.update(draft=True)),
        _broken(lambda e: e.update(prerelease=False)),
        _broken(lambda e: e.update(tag_name="nightly")),
        _broken(lambda e: e.update(target_commitish="main")),
        _broken(lambda e: e.update(assets=[])),
        _broken(lambda e: e["assets"][0].update(name="Decky-Framegen-0000000.zip")),
        _broken(lambda e: e["assets"][0].update(state="starter")),
        _broken(lambda e: e["assets"][0].pop("digest")),
        _broken(lambda e: e["assets"][0].update(digest="md5:00")),
        _broken(lambda e: e["assets"][0].update(browser_download_url="http://example.com/a.zip")),
        _broken(lambda e: e["assets"][0].update(browser_download_url="https://example.com/Decky-Framegen-1a2b3c4.zip")),
        _broken(lambda e: e["assets"][0].update(
            browser_download_url="https://github.com/someone/Decky-Framegen/releases/download/pr-12/Decky-Framegen-1a2b3c4.zip"
        )),
        _broken(lambda e: e["assets"][0].update(
            browser_download_url="https://github.com/arttttt/Decky-Framegen/releases/download/dev/Decky-Framegen-1a2b3c4.zip"
        )),
        "not a release",
    ],
    ids=[
        "draft", "not-prerelease", "not-a-channel-tag", "target-not-a-commit", "no-asset", "asset-of-another-commit",
        "upload-unfinished", "no-digest", "not-sha256", "not-https", "other-host", "other-repository", "other-channel",
        "not-an-object",
    ],
)
def test_anything_that_cannot_be_installed_safely_is_skipped(entry):
    assert dev_build.releases([entry], RUNNING, PLUGIN) == []


def test_a_listing_that_is_not_a_list_has_no_builds():
    assert dev_build.releases({"message": "API rate limit exceeded"}, RUNNING, PLUGIN) == []


def test_only_the_running_channel_and_commit_count_as_installed():
    found = {release.info.channel: release for release in dev_build.releases(listing(), RUNNING, PLUGIN)}
    same_commit_other_channel = dev_build.DevRelease(
        dev_build.build_info(REPOSITORY, "pr-12", DEV_COMMIT), "", "", "https://x/a.zip", "0" * 64
    )

    assert dev_build.state(RUNNING, found["dev"]) == dev_build.INSTALLED
    assert dev_build.state(RUNNING, found["pr-12"]) == dev_build.AVAILABLE
    assert dev_build.state(RUNNING, same_commit_other_channel) == dev_build.AVAILABLE


# ── contract: Decky Loader's installer ───────────────────────────────────────


def _decky_install_plugin(self, artifact="", name="No name", version="dev", hash="", install_type=0):
    """decky-loader v3.3.0 backend/decky_loader/utilities.py:123, the route the Developer section calls."""


def test_the_install_request_fills_deckys_install_plugin_arguments_in_order():
    release = dev_build.releases([pr_12()], RUNNING, PLUGIN)[0]

    request = dev_build.install_request(PLUGIN, release, "/runtime/Decky-Framegen-1a2b3c4.zip")
    bound = inspect.signature(_decky_install_plugin).bind(None, *request).arguments

    assert bound == {
        "self": None,
        # A local file: Decky reads it instead of downloading (browser.py:194, v3.3.0).
        "artifact": "file:///runtime/Decky-Framegen-1a2b3c4.zip",
        "name": PLUGIN,
        "version": "pr-12-1a2b3c4",
        "hash": release.sha256,
        "install_type": 2,
    }
    # "dev" as the version would make Decky re-read the name from the zip (browser.py:242, v3.3.0).
    assert bound["version"] != "dev"


# ── integration: the service and the GitHub client ───────────────────────────


@pytest.fixture
def plugin_dir(tmp_path) -> Path:
    root = tmp_path / "plugins" / PLUGIN
    root.mkdir(parents=True)
    (root / "plugin.json").write_text(json.dumps({"name": PLUGIN}))
    return root


ZIP = b"PK fake development build"
ZIP_SHA256 = hashlib.sha256(ZIP).hexdigest()


class FakeDownload:
    """Stands in for github_releases.download: records each URL and writes the given bytes."""

    def __init__(self, content: bytes = ZIP, error: Exception | None = None):
        self.content, self.error, self.urls = content, error, []

    def __call__(self, url: str, destination: Path, on_progress) -> None:
        self.urls.append(url)
        if self.error:
            raise self.error
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.content)
        half = len(self.content) // 2
        on_progress(half, len(self.content))
        on_progress(len(self.content), len(self.content))


def service(plugin_dir: Path, download: FakeDownload | None = None, reports: list | None = None) -> DevUpdates:
    def report(channel, received, total):
        if reports is not None:
            reports.append((channel, received, total))

    return DevUpdates(
        plugin_dir, github_releases.list_releases, download or FakeDownload(), plugin_dir.parent / "runtime", report
    )


def stamp(plugin_dir: Path, info: dev_build.BuildInfo = RUNNING) -> None:
    (plugin_dir / dev_build.BUILD_INFO_FILENAME).write_text(dev_build.to_json(info))


@pytest.fixture
def github(monkeypatch):
    """A local stand-in for api.github.com; set `.status` and `.body` to change its answer."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            server.requests.append(self.path)
            self.send_response(server.status)
            self.end_headers()
            self.wfile.write(server.body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.status, server.body, server.requests = 200, FIXTURE.read_bytes(), []
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setattr(github_releases, "API_ROOT", f"http://127.0.0.1:{server.server_port}")
    yield server
    server.shutdown()
    server.server_close()


def test_a_release_build_is_not_a_development_build_and_lists_nothing(plugin_dir, github):
    updates = service(plugin_dir)

    assert updates.build() == {"is_dev_build": False}
    assert updates.available_builds() == {"status": "error", "message": "This is not a development build."}
    assert github.requests == []


def test_an_unreadable_identity_is_treated_as_a_release_build(plugin_dir, github):
    (plugin_dir / dev_build.BUILD_INFO_FILENAME).write_text('{"channel": "dev"}')

    assert service(plugin_dir).build() == {"is_dev_build": False}


def test_a_development_build_lists_its_repositorys_builds(plugin_dir, github):
    stamp(plugin_dir)
    updates = service(plugin_dir)

    build = updates.build()
    builds = updates.available_builds()

    assert build == {
        "is_dev_build": True,
        "channel": "dev",
        "commit": DEV_COMMIT,
        "short_commit": "9f2c1a6",
        "title": "main @ 9f2c1a6",
    }
    assert github.requests == [f"/repos/{REPOSITORY}/releases?per_page=100"]
    assert builds["status"] == "success"
    assert [(b["channel"], b["state"]) for b in builds["builds"]] == [
        ("dev", "installed"),
        ("pr-12", "available"),
        ("pr-9", "available"),
    ]
    assert builds["builds"][1] == {
        "channel": "pr-12",
        "commit": PR_COMMIT,
        "short_commit": "1a2b3c4",
        "title": "PR #12: Add a Developer section",
        "published_at": "2026-10-23T10:00:00Z",
        "state": "available",
    }


def test_installing_downloads_the_build_published_now_and_hands_decky_the_file(plugin_dir, github):
    stamp(plugin_dir)
    download, reports = FakeDownload(), []
    updates = service(plugin_dir, download, reports)
    updates.available_builds()
    # A push to the pull request replaced its build after the list was shown.
    replaced = listing()
    pr = next(entry for entry in replaced if entry["tag_name"] == "pr-12")
    pr["target_commitish"] = "2" * 40
    pr["assets"][0]["name"] = "Decky-Framegen-2222222.zip"
    pr["assets"][0]["browser_download_url"] = (
        "https://github.com/arttttt/Decky-Framegen/releases/download/pr-12/Decky-Framegen-2222222.zip"
    )
    pr["assets"][0]["digest"] = f"sha256:{ZIP_SHA256}"
    github.body = json.dumps(replaced).encode()
    stale = write(plugin_dir.parent / "runtime" / "Decky-Framegen-1a2b3c4.zip", b"an earlier download")
    partial = write(plugin_dir.parent / "runtime" / "Decky-Framegen-9f2c1a6.zip.part", b"cut off")

    result = updates.install_request("pr-12")

    downloaded = plugin_dir.parent / "runtime" / "Decky-Framegen-2222222.zip"
    assert len(github.requests) == 2
    assert download.urls == ["https://github.com/arttttt/Decky-Framegen/releases/download/pr-12/Decky-Framegen-2222222.zip"]
    assert downloaded.read_bytes() == ZIP
    assert not stale.exists()
    assert not partial.exists()
    half = len(ZIP) // 2
    assert reports == [("pr-12", half, len(ZIP)), ("pr-12", len(ZIP), len(ZIP))]
    assert result == {
        "status": "success",
        "channel": "pr-12",
        "commit": "2" * 40,
        "short_commit": "2222222",
        "install_request": [f"file://{downloaded}", PLUGIN, "pr-12-2222222", ZIP_SHA256, 2],
    }


def test_a_download_that_fails_or_does_not_match_its_checksum_installs_nothing(plugin_dir, github):
    stamp(plugin_dir)
    failed = service(plugin_dir, FakeDownload(error=github_releases.ReleasesUnavailable("Could not download x"))).install_request("pr-12")
    corrupt = service(plugin_dir, FakeDownload(content=b"not the published build")).install_request("pr-12")

    assert failed == {"status": "error", "message": "Could not download x"}
    assert corrupt == {"status": "error", "message": "The pr-12 build did not match its checksum. Try again."}
    assert list((plugin_dir.parent / "runtime").glob("*.zip")) == []


def test_the_github_client_downloads_a_file_whole_or_not_at_all(tmp_path, github):
    url = f"{github_releases.API_ROOT}/asset.zip"
    github.body = ZIP
    progress = []
    github_releases.download(url, tmp_path / "out" / "asset.zip", lambda received, total: progress.append(received))

    github.status = 404
    with pytest.raises(github_releases.ReleasesUnavailable, match="GitHub answered 404"):
        github_releases.download(url, tmp_path / "out" / "missing.zip")

    assert sorted(path.name for path in (tmp_path / "out").iterdir()) == ["asset.zip"]
    assert (tmp_path / "out" / "asset.zip").read_bytes() == ZIP
    assert progress[-1] == len(ZIP)


def test_installing_a_build_that_is_gone_says_so(plugin_dir, github):
    stamp(plugin_dir)
    github.body = json.dumps([entry for entry in listing() if entry["tag_name"] != "pr-12"]).encode()

    result = service(plugin_dir).install_request("pr-12")

    assert result == {"status": "error", "message": "The pr-12 build is no longer published. Check again."}


def test_installing_from_a_release_build_is_refused(plugin_dir, github):
    assert service(plugin_dir).install_request("dev") == {
        "status": "error",
        "message": "This is not a development build.",
    }
    assert github.requests == []


def test_a_fork_build_lists_the_forks_releases(plugin_dir, github):
    stamp(plugin_dir, dev_build.build_info("someone/Decky-Framegen", "dev", DEV_COMMIT))

    service(plugin_dir).available_builds()

    assert github.requests == ["/repos/someone/Decky-Framegen/releases?per_page=100"]


@pytest.mark.parametrize(
    ("status", "body", "message"),
    [
        (403, b'{"message": "API rate limit exceeded"}', "GitHub answered 403 for arttttt/Decky-Framegen releases"),
        (200, b"<html>", "GitHub sent a release list that is not JSON"),
        (200, b'{"message": "Not Found"}', "GitHub sent something other than a release list"),
    ],
)
def test_github_failures_are_reported_not_raised(plugin_dir, github, status, body, message):
    stamp(plugin_dir)
    github.status, github.body = status, body

    result = service(plugin_dir).available_builds()

    assert result["status"] == "error"
    assert result["message"].startswith(message)


def test_a_plugin_without_a_name_is_reported_not_raised(plugin_dir, github):
    stamp(plugin_dir)
    (plugin_dir / "plugin.json").write_text("{}")

    result = service(plugin_dir).available_builds()

    assert result == {"status": "error", "message": "The plugin's plugin.json has no name."}


def test_an_unreachable_github_is_reported(plugin_dir, monkeypatch):
    stamp(plugin_dir)
    monkeypatch.setattr(github_releases, "API_ROOT", "http://127.0.0.1:9")

    result = service(plugin_dir).available_builds()

    assert result["status"] == "error"
    assert result["message"].startswith("Could not reach GitHub")


def test_the_plugin_answers_for_a_release_build(plugin):
    assert run(plugin.get_dev_build()) == {"is_dev_build": False}


def test_the_plugin_lists_builds_for_a_development_build(plugin, home, tmp_path, github):
    plugin_dir = tmp_path / "plugin"  # the fake decky's DECKY_PLUGIN_DIR
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({"name": PLUGIN}))
    stamp(plugin_dir)

    result = run(plugin.list_dev_builds())

    assert result["status"] == "success"
    assert [b["channel"] for b in result["builds"]] == ["dev", "pr-12", "pr-9"]


def test_the_plugin_reports_download_progress_as_decky_events(plugin, tmp_path, github, monkeypatch):
    plugin_dir = tmp_path / "plugin"  # the fake decky's DECKY_PLUGIN_DIR
    plugin_dir.mkdir()
    (plugin_dir / "plugin.json").write_text(json.dumps({"name": PLUGIN}))
    stamp(plugin_dir)
    published = listing()
    next(entry for entry in published if entry["tag_name"] == "pr-12")["assets"][0]["digest"] = f"sha256:{ZIP_SHA256}"
    github.body = json.dumps(published).encode()
    monkeypatch.setattr(github_releases, "download", FakeDownload())
    events = []

    async def emit(event, *args):
        events.append((event, *args))

    monkeypatch.setattr(main.decky, "emit", emit, raising=False)

    result = run(plugin.dev_install_request("pr-12"))

    assert result["status"] == "success"
    assert result["install_request"][0].startswith("file://")
    assert ("dev_build_download", "pr-12", len(ZIP), len(ZIP)) in events
