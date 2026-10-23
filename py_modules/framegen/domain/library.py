"""The OptiScaler library: which upstream versions exist, how each is laid out, and what to call them.

Versions come straight from OptiScaler's own GitHub releases — `optiscaler/OptiScaler` for
stable builds, `optiscaler/OptiScaler-nightly` for nightly ones. How a version is laid out
in a game (support files in the game root, or in an `OptiScaler/` subfolder) is data per
layout family, not a code branch. Anything the plugin cannot read with certainty — no
archive, several archives, no checksum, a version of no known family — is listed as
unsupported and never downloaded.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

STABLE = "stable"
NIGHTLY = "nightly"

NIGHTLY_SHOWN = 10
"""Nightly builds offered at a time: the newest ones (installed versions stay listed regardless)."""


@dataclass(frozen=True)
class Channel:
    id: str
    repository: str
    """`owner/name` whose GitHub releases publish this channel."""
    prerelease: bool
    """Whether the channel's releases are marked as prereleases (anything else is skipped)."""
    archive: re.Pattern[str]
    """The archive's file name; groups: version, then the build date (YYYYMMDD)."""
    shown: int | None


CHANNELS = {
    STABLE: Channel(
        STABLE,
        "optiscaler/OptiScaler",
        prerelease=False,
        # Optiscaler_0.9.4-final.20260718._MM.7z — the trailing tag (_MM, _AF, _Reup…) is optional.
        archive=re.compile(r"^Optiscaler_(\d+\.\d+\.\d+[a-z]?)-final\.(\d{8})(?:\.[A-Za-z0-9_]+)?\.7z$"),
        shown=None,
    ),
    NIGHTLY: Channel(
        NIGHTLY,
        "optiscaler/OptiScaler-nightly",
        prerelease=True,
        # OptiScaler_v10.0.0-pre1_20261023.7z
        archive=re.compile(r"^OptiScaler_v(\d+\.\d+\.\d+(?:-pre\d+)?)_(\d{8})\.7z$"),
        shown=NIGHTLY_SHOWN,
    ),
}


@dataclass(frozen=True)
class Family:
    """How the versions of one OptiScaler generation are laid out."""

    id: str
    support_dir: str
    """Where the files next to OptiScaler.dll go in a game: "" for the game directory itself."""
    required: frozenset[str]
    """Files an archive of this family must contain, or it is not added to the library."""


FAMILIES = {
    "0.9": Family("0.9", "", frozenset({"OptiScaler.dll", "OptiScaler.ini", "amd_fidelityfx_upscaler_dx12.dll"})),
    "10": Family(
        "10",
        "OptiScaler",
        frozenset({"OptiScaler.dll", "OptiScaler.ini", "OptiScaler/amd_fidelityfx_upscaler_dx12.dll"}),
    ),
}


def family_of(version: str) -> Family | None:
    """The layout family of a version number (0.9.x, 10.x); None for any other."""
    match = re.match(r"^(\d+)\.(\d+)\.", version)
    if not match:
        return None
    major, minor = int(match.group(1)), int(match.group(2))
    if (major, minor) == (0, 9):
        return FAMILIES["0.9"]
    if major == 10:
        return FAMILIES["10"]
    return None


def version_id(channel: str, version: str, date: str) -> str:
    """How the library names a version: `stable-0.9.4`, `nightly-20261023`."""
    return f"{channel}-{date}" if channel == NIGHTLY else f"{channel}-{version}"


NO_ARCHIVE = "no archive this plugin can read"
SEVERAL_ARCHIVES = "more than one archive"
NO_CHECKSUM = "no checksum to verify the download"
UPLOADING = "still uploading"
UNKNOWN_FAMILY = "a version this plugin does not support yet"
ELSEWHERE = "a download outside the OptiScaler release"

_SHA256_DIGEST = re.compile(r"^sha256:([0-9a-f]{64})$")


@dataclass(frozen=True)
class Available:
    """A version published upstream, as the library offers it."""

    id: str
    channel: str
    version: str
    date: str
    published_at: str
    family: str | None
    url: str
    sha256: str
    size: int
    unsupported: str | None
    """Why it can't be downloaded, or None when it can."""


def available(channel_id: str, listing: object) -> list[Available]:
    """The versions a channel publishes, newest first, each either downloadable or saying why not."""
    channel = CHANNELS[channel_id]
    releases = [
        release
        for release in (listing if isinstance(listing, list) else [])
        if isinstance(release, dict) and not release.get("draft") and bool(release.get("prerelease")) == channel.prerelease
    ]
    versions = [_version(channel, release) for release in releases]
    versions.sort(key=lambda v: v.published_at, reverse=True)
    return versions if channel.shown is None else versions[: channel.shown]


def _version(channel: Channel, release: dict) -> Available:
    assets = [a for a in release.get("assets") or [] if isinstance(a, dict)]
    matches = [(a, m) for a in assets if (m := channel.archive.match(str(a.get("name", ""))))]
    tag = str(release.get("tag_name", ""))
    published_at = str(release.get("published_at") or "")
    if len(matches) != 1:
        reason = SEVERAL_ARCHIVES if matches else NO_ARCHIVE
        return Available(f"{channel.id}-{tag}", channel.id, tag, "", published_at, None, "", "", 0, reason)
    asset, match = matches[0]
    version, date = match.group(1), match.group(2)
    digest = _SHA256_DIGEST.match(str(asset.get("digest", "")))
    family = family_of(version)
    url = str(asset.get("browser_download_url", ""))
    expected_url = f"https://github.com/{channel.repository}/releases/download/{tag}/{asset.get('name')}"
    if asset.get("state") != "uploaded":
        reason: str | None = UPLOADING
    elif digest is None:
        reason = NO_CHECKSUM
    elif url != expected_url:
        reason = ELSEWHERE
    elif family is None:
        reason = UNKNOWN_FAMILY
    else:
        reason = None
    return Available(
        id=version_id(channel.id, version, date),
        channel=channel.id,
        version=version,
        date=date,
        published_at=published_at,
        family=family.id if family else None,
        url=url,
        sha256=digest.group(1) if digest else "",
        size=int(asset.get("size") or 0),
        unsupported=reason,
    )


def missing_files(family: Family, extracted: frozenset[str]) -> frozenset[str]:
    """Required files of the family an extracted archive lacks (paths relative to its root, with '/')."""
    return family.required - extracted
