"""Development builds on the device: which one runs, which others exist, how to install one."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from framegen.domain import dev_build
from framegen.infrastructure.files import read_json, sha256
from framegen.infrastructure.github_releases import ReleasesUnavailable

log = logging.getLogger(__name__)

ListReleases = Callable[[str], list]
Download = Callable[..., None]
"""github_releases.download: (url, destination, on_progress)."""
Report = Callable[[str, int, int | None], None]
"""Tells the frontend how a download goes: channel, bytes received, total bytes if known."""


class DevUpdates:
    def __init__(
        self,
        plugin_dir: Path,
        list_releases: ListReleases,
        download: Download,
        downloads_dir: Path,
        report: Report,
    ):
        self.plugin_dir = plugin_dir
        self.list_releases = list_releases
        self.download = download
        self.downloads_dir = downloads_dir
        """Kept by Decky across reinstalls, so the file outlives the plugin that downloaded it."""
        self.report = report

    def _current(self) -> dev_build.BuildInfo | None:
        """The running build's identity; None for a release build (or an unreadable identity, which is logged)."""
        path = self.plugin_dir / dev_build.BUILD_INFO_FILENAME
        if not path.exists():
            return None
        try:
            return dev_build.parse(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.error(f"Ignoring {path}: {exc}")
            return None

    def _plugin_name(self) -> str:
        return str(read_json(self.plugin_dir / "plugin.json").get("name") or "")

    def build(self) -> dict:
        """What the running build is; the Developer section exists only for a development build."""
        current = self._current()
        if current is None:
            return {"is_dev_build": False}
        return {"is_dev_build": True, **_describe(current), "title": current.title}

    def _published(self) -> tuple[dev_build.BuildInfo, str, list[dev_build.DevRelease]] | dict:
        """The running build, the plugin's name and the development builds published now — or an error answer."""
        current = self._current()
        if current is None:
            return {"status": "error", "message": "This is not a development build."}
        try:
            listing = self.list_releases(current.repository)
        except ReleasesUnavailable as exc:
            log.error(f"Listing development builds failed: {exc}")
            return {"status": "error", "message": str(exc)}
        plugin_name = self._plugin_name()
        if not plugin_name:
            return {"status": "error", "message": "The plugin's plugin.json has no name."}
        return current, plugin_name, dev_build.releases(listing, current, plugin_name)

    def available_builds(self) -> dict:
        """Every installable development build, marked installed or available."""
        published = self._published()
        if isinstance(published, dict):
            return published
        current, _, releases = published
        return {
            "status": "success",
            "builds": [
                {
                    **_describe(release.info),
                    "title": release.title,
                    "published_at": release.published_at,
                    "state": dev_build.state(current, release),
                }
                for release in releases
            ],
        }

    def install_request(self, channel: str) -> dict:
        """Download the build published on `channel` right now and return the request that installs it.

        Asked again at install time: a channel's build is replaced on every push, and the
        previous one's download is gone. The file replaces any earlier download.
        """
        published = self._published()
        if isinstance(published, dict):
            return published
        _, plugin_name, releases = published
        release = next((r for r in releases if r.info.channel == channel), None)
        if release is None:
            return {"status": "error", "message": f"The {channel} build is no longer published. Check again."}
        target = self.downloads_dir / dev_build.asset_name(plugin_name, release.info)
        try:
            for stale in self.downloads_dir.glob("*.zip"):
                stale.unlink()
            self.download(release.url, target, lambda received, total: self.report(channel, received, total))
        except (ReleasesUnavailable, OSError) as exc:
            log.error(f"Downloading the {channel} build failed: {exc}")
            return {"status": "error", "message": str(exc)}
        if sha256(target) != release.sha256:
            target.unlink(missing_ok=True)
            return {"status": "error", "message": f"The {channel} build did not match its checksum. Try again."}
        return {
            "status": "success",
            **_describe(release.info),
            "install_request": dev_build.install_request(plugin_name, release, str(target)),
        }


def _describe(info: dev_build.BuildInfo) -> dict:
    return {"channel": info.channel, "commit": info.commit, "short_commit": info.short_commit}
