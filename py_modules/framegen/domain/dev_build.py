"""Development builds: which repository, channel and commit a package was built from.

CI writes this identity into every development package (`build-info.json` at the
plugin root); release packages carry none. The same identity names the package's
version and its release asset, so a device can tell which build it runs.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

BUILD_INFO_FILENAME = "build-info.json"
MAIN_CHANNEL = "dev"
"""The channel built from the main branch; every pull request has its own `pr-<N>`."""

_CHANNEL = re.compile(r"^(dev|pr-[1-9][0-9]*)$")
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_REPOSITORY = re.compile(r"^[A-Za-z0-9-]+/[A-Za-z0-9._-]+$")
_SHORT_COMMIT = 7


@dataclass(frozen=True)
class BuildInfo:
    repository: str
    """`owner/name` on GitHub; its releases hold the other development builds."""
    channel: str
    commit: str

    @property
    def short_commit(self) -> str:
        return self.commit[:_SHORT_COMMIT]


def channel(pull_request: int | None) -> str:
    """The channel of a build: its pull request's own, or the main branch's."""
    return MAIN_CHANNEL if pull_request is None else f"pr-{pull_request}"


def build_info(repository: str, channel: str, commit: str) -> BuildInfo:
    """A validated identity; raises ValueError for anything CI never produces."""
    if not _REPOSITORY.match(repository):
        raise ValueError(f"Not a GitHub repository: {repository!r}")
    if not _CHANNEL.match(channel):
        raise ValueError(f"Not a development channel: {channel!r}")
    if not _COMMIT.match(commit):
        raise ValueError(f"Not a full commit sha: {commit!r}")
    return BuildInfo(repository, channel, commit)


def to_json(info: BuildInfo) -> str:
    return json.dumps({"repository": info.repository, "channel": info.channel, "commit": info.commit}, indent=2) + "\n"


def parse(text: str) -> BuildInfo:
    """The identity from `build-info.json`; raises ValueError when the file is not one."""
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(f"{BUILD_INFO_FILENAME} is not JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{BUILD_INFO_FILENAME} is not an object")
    return build_info(str(data.get("repository", "")), str(data.get("channel", "")), str(data.get("commit", "")))


def version(base: str, info: BuildInfo) -> str:
    """The package version Decky shows, e.g. `0.17-pr-12.1a2b3c4` for base `0.17`."""
    return f"{base}-{info.channel}.{info.short_commit}"


def asset_name(plugin_name: str, info: BuildInfo) -> str:
    """The release asset's file name; the commit in it keeps a cached download from passing for a newer one."""
    return f"{plugin_name}-{info.short_commit}.zip"


# ── Other development builds, from the repository's releases ─────────────────

DECKY_INSTALL_UPDATE = 2
"""decky-loader's install type for a plugin that is already installed
(frontend/src/plugin.ts `InstallType.UPDATE`, v3.3.0); it only words the confirm dialog."""

INSTALLED = "installed"
AVAILABLE = "available"

_SHA256_DIGEST = re.compile(r"^sha256:([0-9a-f]{64})$")


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
    name = asset_name(plugin_name, info)
    asset = next((a for a in entry.get("assets") or [] if isinstance(a, dict) and a.get("name") == name), None)
    if asset is None or asset.get("state") != "uploaded":
        return None
    digest = _SHA256_DIGEST.match(str(asset.get("digest", "")))
    url = str(asset.get("browser_download_url", ""))
    if digest is None or url != download_url(info, name):
        return None
    return DevRelease(
        info=info,
        title=str(entry.get("name") or info.channel),
        published_at=str(entry.get("published_at") or ""),
        url=url,
        sha256=digest.group(1),
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


def install_request(plugin_name: str, release: DevRelease) -> list:
    """The arguments of decky-loader's `utilities/install_plugin(artifact, name, version, hash, install_type)`
    (backend/decky_loader/utilities.py, v3.3.0) that install `release` over the running plugin."""
    label = f"{release.info.channel}-{release.info.short_commit}"
    return [release.url, plugin_name, label, release.sha256, DECKY_INSTALL_UPDATE]
