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
