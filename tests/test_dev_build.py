"""Development build identity: rules (unit) and the CI stamping script (integration)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys

import pytest

from conftest import REPO_ROOT
from framegen.domain import dev_build

COMMIT = "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"
REPOSITORY = "arttttt/Decky-Framegen"

# ── unit: rules ──────────────────────────────────────────────────────────────


def test_main_and_every_pull_request_have_a_channel_of_their_own():
    assert dev_build.channel(None) == "dev"
    assert dev_build.channel(12) == "pr-12"
    assert dev_build.build_info(REPOSITORY, dev_build.channel(12), COMMIT).channel == "pr-12"


@pytest.mark.parametrize("channel", ["", "main", "pr-", "pr-0", "pr-12x", "release", "DEV"])
def test_anything_else_is_not_a_channel(channel):
    with pytest.raises(ValueError, match="Not a development channel"):
        dev_build.build_info(REPOSITORY, channel, COMMIT)


@pytest.mark.parametrize("commit", ["", COMMIT[:7], COMMIT + "0", COMMIT.upper(), "g" * 40])
def test_only_a_full_lowercase_sha_is_a_commit(commit):
    with pytest.raises(ValueError, match="Not a full commit sha"):
        dev_build.build_info(REPOSITORY, "dev", commit)


@pytest.mark.parametrize("repository", ["", "Decky-Framegen", "a/b/c", "owner/", "/name", "owner/na me"])
def test_only_owner_slash_name_is_a_repository(repository):
    with pytest.raises(ValueError, match="Not a GitHub repository"):
        dev_build.build_info(repository, "dev", COMMIT)


def test_a_build_carries_its_title_but_is_identified_without_it():
    titled = dev_build.build_info(REPOSITORY, "pr-12", COMMIT, "Add a\nsection")

    assert titled.title == "PR #12: Add a section"
    assert dev_build.parse(dev_build.to_json(titled)).title == "PR #12: Add a section"
    assert titled == dev_build.build_info(REPOSITORY, "pr-12", COMMIT)


def test_a_file_without_a_title_gets_the_channels_default():
    text = '{"repository": "%s", "channel": "pr-12", "commit": "%s"}' % (REPOSITORY, COMMIT)

    assert dev_build.parse(text).title == "PR #12"


def test_build_info_round_trips_through_its_file():
    info = dev_build.build_info(REPOSITORY, "pr-7", COMMIT)

    assert dev_build.parse(dev_build.to_json(info)) == info


@pytest.mark.parametrize(
    "text",
    [
        "not json",
        "[]",
        '{"repository": "%s", "channel": "dev"}' % REPOSITORY,
        '{"channel": "dev", "commit": "%s"}' % COMMIT,
        '{"repository": "%s", "channel": "main", "commit": "%s"}' % (REPOSITORY, COMMIT),
    ],
)
def test_a_file_that_is_not_a_build_identity_is_rejected(text):
    with pytest.raises(ValueError):
        dev_build.parse(text)


def test_version_and_asset_name_carry_channel_and_short_commit():
    info = dev_build.build_info(REPOSITORY, "pr-12", COMMIT)

    assert dev_build.version("2026.10.04", info) == "2026.10.04-pr-12.1a2b3c4"
    assert dev_build.asset_name("Decky-Framegen", info) == "Decky-Framegen-1a2b3c4.zip"


def test_a_release_is_titled_after_main_or_its_pull_request():
    assert dev_build.release_title(dev_build.build_info(REPOSITORY, "dev", COMMIT)) == "main @ 1a2b3c4"
    pr = dev_build.build_info(REPOSITORY, "pr-12", COMMIT)
    assert dev_build.release_title(pr, "Add a Developer section") == "PR #12: Add a Developer section"
    assert dev_build.release_title(pr, "  Two\nlines\r\n ") == "PR #12: Two lines"
    assert dev_build.release_title(pr, " ") == "PR #12"


# ── integration: the stamping script CI runs ─────────────────────────────────


@pytest.fixture
def checkout(tmp_path):
    """The files the script touches, copied from the repository."""
    root = tmp_path / "checkout"
    (root / "defaults").mkdir(parents=True)
    for name in ("package.json", "plugin.json"):
        shutil.copy(REPO_ROOT / name, root / name)
    return root


def stamp(root, *args):
    return subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stamp_dev_build.py"), "--root", str(root), "--repository", REPOSITORY, *args],
        capture_output=True,
        text=True,
    )


def test_stamping_writes_the_identity_and_the_version_and_reports_both(checkout):
    base = "2026.10.04"  # the build day, as releases are named

    result = stamp(
        checkout, "--pull-request", "12", "--pull-request-title", "Add\na section", "--commit", COMMIT, "--date", "2026-10-04"
    )

    assert result.returncode == 0, result.stderr
    info = dev_build.parse((checkout / "defaults" / dev_build.BUILD_INFO_FILENAME).read_text())
    assert info == dev_build.build_info(REPOSITORY, "pr-12", COMMIT)
    assert info.title == "PR #12: Add a section"
    package = json.loads((checkout / "package.json").read_text())
    assert package["version"] == f"{base}-pr-12.1a2b3c4"
    assert result.stdout.splitlines() == [
        "channel=pr-12",
        f"version={base}-pr-12.1a2b3c4",
        "asset=Decky-Framegen-1a2b3c4.zip",
        "title=PR #12: Add a section",
    ]


def test_a_build_of_main_is_stamped_for_the_main_channel(checkout):
    result = stamp(checkout, "--commit", COMMIT)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[0] == "channel=dev"


def test_stamping_refuses_an_invalid_identity_and_changes_nothing(checkout):
    before = (checkout / "package.json").read_text()

    result = stamp(checkout, "--pull-request", "12", "--commit", COMMIT[:7])

    assert result.returncode == 2
    assert "Not a full commit sha" in result.stderr
    assert (checkout / "package.json").read_text() == before
    assert not (checkout / "defaults" / dev_build.BUILD_INFO_FILENAME).exists()
