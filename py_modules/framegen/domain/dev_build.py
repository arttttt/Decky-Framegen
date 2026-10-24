"""Builds of the plugin: which repository, channel and commit a package was built from, and the other
builds a device can switch to.

CI writes this identity into every package it publishes (`build-info.json` at the plugin root): a
release on the stable channel, a development build on main's channel or its pull request's. A package
without one (built by hand, or a fork's pull request) can't update itself. The identity names the
package's version and its release asset, so a device can tell which build it runs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field, replace

from . import release_assets, release_version

BUILD_INFO_FILENAME = "build-info.json"
STABLE_CHANNEL = "stable"
"""Releases."""
MAIN_CHANNEL = "dev"
"""The development channel built from the main branch; every pull request has its own `pr-<N>`."""

_CHANNEL = re.compile(r"^(stable|dev|pr-[1-9][0-9]*)$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
_SHORT_COMMIT = 7


@dataclass(frozen=True)
class BuildInfo:
    repository: str
    """`owner/name` on GitHub; its releases hold the other development builds."""
    channel: str
    commit: str
    title: str = field(default="", compare=False)
    """How the build is named on the device (`Decky Framegen 2026.10.24`, `Dev build · main @ 1a2b3c4`,
    `Dev build · PR #12: <title>`); not part of its identity."""

    @property
    def short_commit(self) -> str:
        return self.commit[:_SHORT_COMMIT]


def channel(pull_request: int | None) -> str:
    """The channel of a build: its pull request's own, or the main branch's."""
    return MAIN_CHANNEL if pull_request is None else f"pr-{pull_request}"


def is_development(info: BuildInfo) -> bool:
    """Whether a build is a development one (main's or a pull request's), not a release."""
    return info.channel != STABLE_CHANNEL


def build_info(
    repository: str, channel: str, commit: str, pull_request_title: str = "", version: str = ""
) -> BuildInfo:
    """A validated identity, titled after its release version, main or its pull request; raises ValueError
    for anything CI never produces."""
    if not _REPOSITORY.match(repository):
        raise ValueError(f"Not a GitHub repository: {repository!r}")
    if not _CHANNEL.match(channel):
        raise ValueError(f"Not a build channel: {channel!r}")
    if not _COMMIT.match(commit):
        raise ValueError(f"Not a full commit sha: {commit!r}")
    info = BuildInfo(repository, channel, commit)
    return replace(info, title=release_title(info, pull_request_title, version))


def to_json(info: BuildInfo) -> str:
    fields = {"repository": info.repository, "channel": info.channel, "commit": info.commit, "title": info.title}
    return json.dumps(fields, indent=2) + "\n"


def parse(text: str) -> BuildInfo:
    """The identity from `build-info.json`; raises ValueError when the file is not one."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"{BUILD_INFO_FILENAME} is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{BUILD_INFO_FILENAME} is not an object")
    info = build_info(str(data.get("repository", "")), str(data.get("channel", "")), str(data.get("commit", "")))
    title = data.get("title")
    return replace(info, title=" ".join(title.split())) if isinstance(title, str) and title.strip() else info


def version(base: str, info: BuildInfo) -> str:
    """The package version Decky shows, e.g. `2026.10.24-pr-12.1a2b3c4` for base `2026.10.24`."""
    return f"{base}-{info.channel}.{info.short_commit}"


DEV_TITLE_PREFIX = "Dev build · "
"""Sets a development build apart from a release (`Decky Framegen 2026.10.24`) on the releases page."""


RELEASE_TITLE_PREFIX = "Decky Framegen "


def release_title(info: BuildInfo, pull_request_title: str = "", version: str = "") -> str:
    """The name of the release that publishes a build, shown on the device next to each build."""
    if info.channel == STABLE_CHANNEL:
        return f"{RELEASE_TITLE_PREFIX}{version}".strip()
    if info.channel == MAIN_CHANNEL:
        return f"{DEV_TITLE_PREFIX}main @ {info.short_commit}"
    number = info.channel.removeprefix("pr-")
    title = " ".join(pull_request_title.split())  # one line, whatever the pull request's title holds
    return f"{DEV_TITLE_PREFIX}PR #{number}: {title}" if title else f"{DEV_TITLE_PREFIX}PR #{number}"


def asset_name(plugin_name: str, info: BuildInfo) -> str:
    """The release asset's file name; the commit in it keeps a cached download from passing for a newer one."""
    return f"{plugin_name}-{info.short_commit}.zip"


# ── Other development builds, from the repository's releases ─────────────────

DECKY_INSTALL_UPDATE = 2
"""decky-loader's install type for a plugin that is already installed
(frontend/src/plugin.ts `InstallType.UPDATE`, v3.3.0); it only words the confirm dialog."""

INSTALLED = "installed"
AVAILABLE = "available"



@dataclass(frozen=True)
class DevRelease:
    """A development build published as a prerelease, installable on the device."""

    info: BuildInfo
    title: str
    published_at: str
    url: str
    sha256: str


def releases(listing: object, current: BuildInfo, plugin_name: str) -> list[DevRelease]:
    """The installable development builds in a GitHub releases listing: main's first, then pull requests, newest first.

    A release qualifies when it is a published prerelease tagged with a channel, its target is a full
    commit, and it holds exactly the asset that commit's build is named after, uploaded and with a
    sha256 digest Decky can check the download against, served from the repository's own release
    downloads. Anything else is skipped.
    """
    found = [release for entry in (listing if isinstance(listing, list) else []) if (release := _release(entry, current, plugin_name))]
    return sorted(found, key=lambda release: _channel_order(release.info.channel))


def _release(entry: object, current: BuildInfo, plugin_name: str) -> DevRelease | None:
    if not isinstance(entry, dict) or entry.get("draft") or not entry.get("prerelease"):
        return None
    try:
        info = build_info(current.repository, str(entry.get("tag_name", "")), str(entry.get("target_commitish", "")))
    except ValueError:
        return None
    if not is_development(info):
        return None
    name = asset_name(plugin_name, info)
    asset = next((a for a in entry.get("assets") or [] if isinstance(a, dict) and a.get("name") == name), None)
    if asset is None or asset.get("state") != "uploaded":
        return None
    digest = release_assets.sha256(asset)
    url = str(asset.get("browser_download_url", ""))
    if digest is None or url != download_url(info, name):
        return None
    return DevRelease(
        info=info,
        title=str(entry.get("name") or info.channel),
        published_at=str(entry.get("published_at") or ""),
        url=url,
        sha256=digest,
    )


def download_url(info: BuildInfo, asset: str) -> str:
    """Where GitHub serves a release asset of the build's own repository; nothing else is downloaded."""
    return f"https://github.com/{info.repository}/releases/download/{info.channel}/{asset}"


def _channel_order(channel: str) -> tuple[int, int]:
    return (0, 0) if channel == MAIN_CHANNEL else (1, -int(channel.removeprefix("pr-")))


def state(current: BuildInfo, release: DevRelease) -> str:
    """`installed` when the release is the build running now, `available` otherwise."""
    same = (release.info.channel, release.info.commit) == (current.channel, current.commit)
    return INSTALLED if same else AVAILABLE


def dev_label(release: DevRelease) -> str:
    """The version Decky's confirm dialog names a development build by."""
    return f"{release.info.channel}-{release.info.short_commit}"


def install_request(plugin_name: str, label: str, sha256: str, downloaded: str, install_type: int) -> list:
    """The arguments of decky-loader's `utilities/install_plugin(artifact, name, version, hash, install_type)`
    (backend/decky_loader/utilities.py, v3.3.0) that install a downloaded build over the running plugin.

    The plugin downloads the zip itself and hands Decky the file (`file://`, browser.py:194, v3.3.0):
    Decky's own download from a URL never reached GitHub on a Bazzite device, while the plugin's does.
    Decky still checks the file against the sha256.
    """
    return [f"file://{downloaded}", plugin_name, label, sha256, install_type]


# ── Releases, and switching to one ───────────────────────────────────────────

RELEASE_ASSET = "Decky-Framegen.zip"
"""A release's one asset; the name people download by hand (release.yml)."""

DECKY_INSTALL_DOWNGRADE = 3
DECKY_INSTALL_OVERWRITE = 4
"""decky-loader's other install types (InstallType, v3.3.0); like UPDATE, they only word the confirm dialog."""

UPDATE = "update"
SWITCH = "switch"
NONE = "none"


@dataclass(frozen=True)
class StableRelease:
    """The newest release, installable on the device."""

    version: str
    title: str
    published_at: str
    url: str
    sha256: str


def stable_release(entry: object, repository: str) -> StableRelease | None:
    """The release in GitHub's latest-release answer, when it is one a device can install: published, not a
    prerelease, tagged with a release version, holding the release asset uploaded with a sha256 digest and
    served from the repository's own release downloads."""
    if not isinstance(entry, dict) or entry.get("draft") or entry.get("prerelease"):
        return None
    tag = str(entry.get("tag_name", ""))
    if not release_version.is_release(tag):
        return None
    asset = next((a for a in entry.get("assets") or [] if isinstance(a, dict) and a.get("name") == RELEASE_ASSET), None)
    if asset is None or asset.get("state") != "uploaded":
        return None
    digest = release_assets.sha256(asset)
    url = str(asset.get("browser_download_url", ""))
    if digest is None or url != f"https://github.com/{repository}/releases/download/{tag}/{RELEASE_ASSET}":
        return None
    return StableRelease(
        version=tag,
        title=str(entry.get("name") or f"{RELEASE_TITLE_PREFIX}{tag}"),
        published_at=str(entry.get("published_at") or ""),
        url=url,
        sha256=digest,
    )


def stable_offer(current: BuildInfo, running_version: str, release: StableRelease | None) -> str:
    """What the device offers for the newest release: UPDATE when a release build is older than it, SWITCH
    from a development build (whatever their versions), else NONE."""
    if release is None:
        return NONE
    if is_development(current):
        return SWITCH
    running, latest = release_version.key(running_version), release_version.key(release.version)
    return UPDATE if running is not None and latest is not None and latest > running else NONE


def install_type(running_version: str, version: str) -> int:
    """How Decky's confirm dialog words installing `version` over the running one: an update, a downgrade,
    or an overwrite of the same day's build."""
    running, target = release_version.key(running_version), release_version.key(version)
    if running is None or target is None or target > running:
        return DECKY_INSTALL_UPDATE
    return DECKY_INSTALL_OVERWRITE if target == running else DECKY_INSTALL_DOWNGRADE


def developer_mode(current: BuildInfo, turned_on: bool) -> bool:
    """Whether the device offers development builds: the user turned it on, or one is running already."""
    return turned_on or is_development(current)
