"""Calendar versions for releases: the rule (unit) and the script that stamps a release build (integration)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import date

import pytest

from conftest import REPO_ROOT
from framegen.domain import release_version

DAY = date(2026, 10, 4)


def test_a_day_is_zero_padded_so_versions_sort_as_text():
    assert release_version.day(DAY) == "2026.10.04"
    assert release_version.day(date(2026, 1, 9)) < release_version.day(date(2026, 10, 4))


@pytest.mark.parametrize(
    ("tags", "version"),
    [
        ([], "2026.10.04"),
        (["v2026.10.03", "v2026.10.03.1", "dev", "pr-12"], "2026.10.04"),  # other days and channels don't count
        (["v2026.10.04"], "2026.10.04.1"),
        (["v2026.10.04", "v2026.10.04.1", "v2026.10.04.2"], "2026.10.04.3"),
        (["v2026.10.04.5", "v2026.10.04"], "2026.10.04.6"),  # the highest count, whatever the order
        (["v2026.10.04-rc"], "2026.10.04"),  # not a release tag
    ],
)
def test_a_release_is_named_after_its_day_and_counts_on_from_that_days_releases(tags, version):
    assert release_version.next_release(DAY, tags) == version


def test_the_tag_names_the_version():
    assert release_version.tag("2026.10.04.1") == "v2026.10.04.1"


def test_stamping_a_release_build_writes_and_reports_the_version(tmp_path):
    root = tmp_path / "checkout"
    root.mkdir()
    shutil.copy(REPO_ROOT / "package.json", root / "package.json")

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scripts" / "stamp_release.py"), "--root", str(root), "--date", "2026-10-04",
         "--existing-tag", "v2026.10.04", "--existing-tag", "dev"],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads((root / "package.json").read_text())["version"] == "2026.10.04.1"
    assert result.stdout.splitlines() == ["version=2026.10.04.1", "tag=v2026.10.04.1"]
    assert not (root / "defaults").exists()  # no development identity
