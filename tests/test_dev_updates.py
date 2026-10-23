"""Other development builds: picking them from releases (unit) and listing them on the device (integration)."""

from __future__ import annotations

import copy
import http.server
import inspect
import json
import threading
from pathlib import Path

import pytest

from conftest import run
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
        "not a release",
    ],
    ids=[
        "draft", "not-prerelease", "not-a-channel-tag", "target-not-a-commit", "no-asset", "asset-of-another-commit",
        "upload-unfinished", "no-digest", "not-sha256", "not-https", "not-an-object",
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

    request = dev_build.install_request(PLUGIN, release)
    bound = inspect.signature(_decky_install_plugin).bind(None, *request).arguments

    assert bound == {
        "self": None,
        "artifact": release.url,
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
    service = DevUpdates(plugin_dir, github_releases.list_releases)

    assert service.build() == {"is_dev_build": False}
    assert service.available_builds() == {"status": "error", "message": "This is not a development build."}
    assert github.requests == []


def test_an_unreadable_identity_is_treated_as_a_release_build(plugin_dir, github):
    (plugin_dir / dev_build.BUILD_INFO_FILENAME).write_text('{"channel": "dev"}')

    assert DevUpdates(plugin_dir, github_releases.list_releases).build() == {"is_dev_build": False}


def test_a_development_build_lists_its_repositorys_builds_ready_to_install(plugin_dir, github):
    stamp(plugin_dir)
    service = DevUpdates(plugin_dir, github_releases.list_releases)

    build = service.build()
    builds = service.available_builds()

    assert build == {"is_dev_build": True, "channel": "dev", "commit": DEV_COMMIT, "short_commit": "9f2c1a6"}
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
        "install_request": [
            "https://github.com/arttttt/Decky-Framegen/releases/download/pr-12/Decky-Framegen-1a2b3c4.zip",
            PLUGIN,
            "pr-12-1a2b3c4",
            "7e00ac50b658c754697f810ff3c91e881552081ddb7743b7f72ef500f1c5ca70",
            2,
        ],
    }


def test_a_fork_build_lists_the_forks_releases(plugin_dir, github):
    stamp(plugin_dir, dev_build.build_info("someone/Decky-Framegen", "dev", DEV_COMMIT))

    DevUpdates(plugin_dir, github_releases.list_releases).available_builds()

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

    result = DevUpdates(plugin_dir, github_releases.list_releases).available_builds()

    assert result["status"] == "error"
    assert result["message"].startswith(message)


def test_an_unreachable_github_is_reported(plugin_dir, monkeypatch):
    stamp(plugin_dir)
    monkeypatch.setattr(github_releases, "API_ROOT", "http://127.0.0.1:9")

    result = DevUpdates(plugin_dir, github_releases.list_releases).available_builds()

    assert result["status"] == "error"
    assert result["message"].startswith("Could not reach GitHub")


def test_the_plugin_answers_for_a_release_build(plugin):
    assert run(plugin.get_dev_build()) == {"is_dev_build": False}
