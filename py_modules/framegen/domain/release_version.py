"""Calendar versions: a build is named after the day it is made (2026.10.24), and a second release
the same day after its count (2026.10.24.1). Nobody picks a number."""

from __future__ import annotations

import re
from datetime import date



def day(today: date) -> str:
    """The day's version, zero-padded so versions sort as text: 2026.10.04."""
    return today.strftime("%Y.%m.%d")


def next_release(today: date, existing_tags: list[str]) -> str:
    """The version a release made today gets: the day, or the day with the next count when releases
    were already made that day. `existing_tags` are the repository's tags: a release's tag is its version."""
    base = day(today)
    taken = re.compile(rf"^{re.escape(base)}(?:\.(\d+))?$")
    counts = [int(match.group(1) or 0) for tag in existing_tags if (match := taken.match(tag.strip()))]
    return base if not counts else f"{base}.{max(counts) + 1}"


def tag(version: str) -> str:
    """A release's tag: the bare version, 2026.10.24."""
    return version


_VERSION = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})(?:\.(\d+))?")


def key(version: str) -> tuple[int, int, int, int] | None:
    """A version as something to compare: its day and that day's count. A development build's version
    (2026.10.24-dev.1a2b3c4) compares as its day; None for anything that isn't a calendar version."""
    match = _VERSION.match(version.strip())
    if not match:
        return None
    year, month, day_, count = match.groups()
    return int(year), int(month), int(day_), int(count or 0)


def is_release(version: str) -> bool:
    """Whether a tag or version is exactly a release's: 2026.10.24 or 2026.10.24.1, nothing after."""
    match = _VERSION.match(version)
    return match is not None and match.end() == len(version)
