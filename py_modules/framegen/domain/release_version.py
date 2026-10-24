"""Calendar versions: a build is named after the day it is made (2026.10.24), and a second release
the same day after its count (2026.10.24.1). Nobody picks a number."""

from __future__ import annotations

import re
from datetime import date

TAG_PREFIX = "v"


def day(today: date) -> str:
    """The day's version, zero-padded so versions sort as text: 2026.10.04."""
    return today.strftime("%Y.%m.%d")


def next_release(today: date, existing_tags: list[str]) -> str:
    """The version a release made today gets: the day, or the day with the next count when releases
    were already made that day. `existing_tags` are the repository's tags (v2026.10.24, ...)."""
    base = day(today)
    taken = re.compile(rf"^{re.escape(TAG_PREFIX + base)}(?:\.(\d+))?$")
    counts = [int(match.group(1) or 0) for tag in existing_tags if (match := taken.match(tag.strip()))]
    return base if not counts else f"{base}.{max(counts) + 1}"


def tag(version: str) -> str:
    return f"{TAG_PREFIX}{version}"
