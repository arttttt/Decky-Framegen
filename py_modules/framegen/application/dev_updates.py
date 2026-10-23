"""Development builds on the device: which one runs, which others exist, how to install one."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from framegen.domain import dev_build
from framegen.infrastructure.files import read_json
from framegen.infrastructure.github_releases import ReleasesUnavailable

log = logging.getLogger(__name__)

ListReleases = Callable[[str], list]


class DevUpdates:
    def __init__(self, plugin_dir: Path, list_releases: ListReleases):
        self.plugin_dir = plugin_dir
        self.list_releases = list_releases

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
        return {"is_dev_build": True, **_describe(current)}

    def available_builds(self) -> dict:
        """Every installable development build, marked installed or available, with the request that installs it."""
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
        return {
            "status": "success",
            "builds": [
                {
                    **_describe(release.info),
                    "title": release.title,
                    "published_at": release.published_at,
                    "state": dev_build.state(current, release),
                    "install_request": dev_build.install_request(plugin_name, release),
                }
                for release in dev_build.releases(listing, current, plugin_name)
            ],
        }


def _describe(info: dev_build.BuildInfo) -> dict:
    return {"channel": info.channel, "commit": info.commit, "short_commit": info.short_commit}
