"""Calendar versions for releases: the rule (unit) and the script that stamps a release build (integration)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date

import pytest

from conftest import REPO_ROOT
from framegen.domain import dev_build, release_version

DAY = date(2026, 10, 4)


def test_a_day_is_zero_padded_so_versions_sort_as_text():
    assert release_version.day(DAY) == "2026.10.04"
    assert release_version.day(date(2026, 1, 9)) < release_version.day(date(2026, 10, 4))


@pytest.mark.parametrize(
    ("tags", "version"),
    [
        ([], "2026.10.04"),
        (["2026.10.03", "2026.10.03.1", "dev", "pr-12"], "2026.10.04"),  # other days and channels don't count
        (["2026.10.04"], "2026.10.04.1"),
        (["2026.10.04", "2026.10.04.1", "2026.10.04.2"], "2026.10.04.3"),
        (["2026.10.04.5", "2026.10.04"], "2026.10.04.6"),  # the highest count, whatever the order
        (["2026.10.04-rc", "v2026.10.04"], "2026.10.04"),  # not release tags
    ],
)
def test_a_release_is_named_after_its_day_and_counts_on_from_that_days_releases(tags, version):
    assert release_version.next_release(DAY, tags) == version


def test_the_tag_names_the_version():
    assert release_version.tag("2026.10.04.1") == "2026.10.04.1"


def test_stamping_a_release_build_writes_and_reports_the_version(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    shutil.copy(REPO_ROOT / "package.json", root / "package.json")

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stamp_release.py"), "--root", str(root), "--date", "2026-10-04",
         "--existing-tag", "2026.10.04", "--existing-tag", "dev",
         "--repository", "arttttt/DeckyScaler", "--commit", "1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads((root / "package.json").read_text())["version"] == "2026.10.04.1"
    assert result.stdout.splitlines() == ["version=2026.10.04.1", "tag=2026.10.04.1", "channel=stable"]
    # The release knows its repository, to find its updates, and is on the stable channel.
    info = dev_build.parse((root / "defaults" / dev_build.BUILD_INFO_FILENAME).read_text())
    assert (info.repository, info.channel, info.title) == ("arttttt/DeckyScaler", "stable", "DeckyScaler 2026.10.04.1")
