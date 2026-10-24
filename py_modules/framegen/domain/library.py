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

from . import release_assets

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
    """One OptiScaler generation: what its archive must hold and where OptiScaler looks for its files.

    A version's archive is already laid out as the game needs it (0.9 keeps everything next to
    OptiScaler.dll, 10 puts the support files in an OptiScaler/ subfolder), so placing it is the
    same for every family.
    """

    id: str
    required: frozenset[str]
    """Files an archive of this family must contain, or it is not added to the library."""
    main_dir: str
    """Where OptiScaler looks for its own files, such as AMD's FSR 4 driver DLL, relative to the game's
    directory: its OptiScaler/ subfolder when there is one, else the directory itself (dllmain.cpp, MainDllPath)."""


FAMILIES = {
    "0.9": Family(
        "0.9",
        frozenset({"OptiScaler.dll", "OptiScaler.ini", "amd_fidelityfx_upscaler_dx12.dll"}),
        "",
    ),
    "10": Family(
        "10",
        frozenset({"OptiScaler.dll", "OptiScaler.ini", "OptiScaler/amd_fidelityfx_upscaler_dx12.dll"}),
        "OptiScaler",
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
    # A version re-released upstream (a fixed re-upload as a new release) is offered once: the newest.
    newest: list[Available] = []
    for version in versions:
        if all(version.id != kept.id for kept in newest):
            newest.append(version)
    return newest if channel.shown is None else newest[: channel.shown]


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
    digest = release_assets.sha256(asset)
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
        sha256=digest or "",
        size=int(asset.get("size") or 0),
        unsupported=reason,
    )


def missing_files(family: Family, extracted: frozenset[str]) -> frozenset[str]:
    """Required files of the family an extracted archive lacks (paths relative to its root, with '/')."""
    return family.required - extracted


# ── The library on the device ────────────────────────────────────────────────

ENTRY_FILENAME = "entry.json"
FILES_DIRNAME = "files"
"""versions/<id>/files holds the unpacked archive as is; versions/<id>/entry.json describes it."""

SPACE_FACTOR = 5
"""Free space an install needs, as a multiple of the archive: the archive plus the unpacked files
(OptiScaler archives unpack to about four times their size)."""


def space_needed(archive_size: int) -> int:
    return archive_size * SPACE_FACTOR


@dataclass(frozen=True)
class Installed:
    """A version in the library, as its entry.json records it."""

    id: str
    channel: str
    version: str
    date: str
    family: str
    source_url: str
    sha256: str
    installed_at: str


def entry(version: Available, installed_at: str) -> Installed:
    if version.family is None:
        raise ValueError(f"{version.id} has no layout family")
    return Installed(
        version.id, version.channel, version.version, version.date, version.family, version.url, version.sha256,
        installed_at,
    )


def entry_json(installed: Installed) -> dict:
    return dict(installed.__dict__)


def parse_entry(data: object) -> Installed | None:
    """An entry.json's version, or None when the file isn't one (the directory is then not in the library)."""
    if not isinstance(data, dict):
        return None
    try:
        installed = Installed(**{name: str(data[name]) for name in Installed.__dataclass_fields__})
    except KeyError:
        return None
    return installed if installed.family in FAMILIES and installed.channel in CHANNELS else None


def newest_first(installed: list[Installed]) -> list[Installed]:
    return sorted(installed, key=lambda entry: (entry.date, entry.id), reverse=True)


def version_to_patch_with(installed: list[Installed], patched_with: str | None) -> Installed | None:
    """The version a patch that names none uses: the one the game is already patched with, so a newer
    download never switches it silently, else the newest downloaded. None when nothing is downloaded."""
    current = next((entry for entry in installed if entry.id == patched_with), None)
    if current is not None:
        return current
    newest = newest_first(installed)
    return newest[0] if newest else None


def choice_json(installed: Installed, size: int) -> dict:
    """An installed version as patching offers it and the library lists it; `size` is its bytes on disk."""
    return {
        "id": installed.id,
        "version": installed.version,
        "channel": installed.channel,
        "date": installed.date,
        "size": size,
    }


def newer_in_channel(installed: list[Installed], version_id: str | None) -> str | None:
    """The newest installed version of the same channel built after `version_id`, if any: a game
    patched with `version_id` could be patched again with it."""
    current = next((entry for entry in installed if entry.id == version_id), None)
    if current is None:
        return None
    newer = [entry for entry in installed if entry.channel == current.channel and entry.date > current.date]
    return newest_first(newer)[0].id if newer else None


INSTALLED = "installed"
AVAILABLE = "available"
UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Row:
    """One version of a channel as the download dialog lists it."""

    id: str
    version: str
    date: str
    family: str | None
    state: str
    reason: str | None
    size: int


def catalog(installed: list[Installed], published: list[Available], sizes: dict[str, int]) -> list[Row]:
    """A channel's versions, newest first: every installed one (also those upstream no longer lists)
    as installed, then what upstream publishes, downloadable or not. `sizes` holds installed sizes."""
    installed_ids = {entry.id for entry in installed}
    rows = [
        Row(entry.id, entry.version, entry.date, entry.family, INSTALLED, None, sizes.get(entry.id, 0))
        for entry in installed
    ]
    rows += [
        Row(
            version.id, version.version, version.date, version.family,
            UNSUPPORTED if version.unsupported else AVAILABLE, version.unsupported, version.size,
        )
        for version in published
        if version.id not in installed_ids
    ]
    return sorted(rows, key=lambda row: row.date, reverse=True)


def removal_refused(version_id: str, installed_ids: set[str], linked_games: list[str]) -> str | None:
    """Why a version can't be removed, or None. A version games are linked to stays while they are:
    removing it would break them. Games patched by copies don't hold it."""
    if version_id not in installed_ids:
        return f"{version_id} is not in the library."
    if linked_games:
        return f"{', '.join(linked_games)} use {version_id} through links. Unpatch them first."
    return None
