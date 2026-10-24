"""Updating the plugin on the device: which build runs, the newest release, the development builds Developer
mode offers, and downloading one for Decky to install."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from framegen.domain import dev_build
from framegen.infrastructure.files import read_json, sha256, write_json
from framegen.infrastructure.github_releases import ReleasesUnavailable

log = logging.getLogger(__name__)

ListReleases = Callable[[str], list]
LatestRelease = Callable[[str], "dict | None"]
Download = Callable[[str, Path, Callable[[int, int | None], None]], None]
"""github_releases.download: (url, destination, on_progress(received, total))."""
Report = Callable[[str, int, int | None], None]
"""Tells the frontend how a download goes: channel, bytes received, total bytes if known."""

UNKNOWN_BUILD = "This build doesn't know where it came from (built by hand?), so it can't update itself. Install a release."
DEVELOPER_MODE_OFF = "Turn on Developer mode to install development builds."
DEVELOPER_MODE_KEY = "developer_mode"
NO_NAME = "The plugin's plugin.json has no name."


class PluginUpdates:
    def __init__(
        self,
        plugin_dir: Path,
        settings_path: Path,
        list_releases: ListReleases,
        latest_release: LatestRelease,
        download: Download,
        downloads_dir: Path,
        report: Report,
    ):
        self.plugin_dir = plugin_dir
        self.settings_path = settings_path
        """Where Developer mode is kept; Decky keeps the plugin's settings across reinstalls."""
        self.list_releases = list_releases
        self.latest_release = latest_release
        self.download = download
        self.downloads_dir = downloads_dir
        """Kept by Decky across reinstalls, so the file outlives the plugin that downloaded it."""
        self.report = report

    # ── the running build ────────────────────────────────────────────────────

    def _current(self) -> dev_build.BuildInfo | None:
        """The running build's identity; None when the package has none (or an unreadable one, which is logged)."""
        path = self.plugin_dir / dev_build.BUILD_INFO_FILENAME
        if not path.exists():
            return None
        try:
            return dev_build.parse(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            log.error(f"Ignoring {path}: {exc}")
            return None

    def _version(self) -> str:
        return str(read_json(self.plugin_dir / "package.json").get("version") or "")

    def _plugin_name(self) -> str:
        return str(read_json(self.plugin_dir / "plugin.json").get("name") or "")

    def _developer_mode(self, current: dev_build.BuildInfo) -> bool:
        return dev_build.developer_mode(current, read_json(self.settings_path).get(DEVELOPER_MODE_KEY) is True)

    def build(self) -> dict:
        """What the running build is, and whether Developer mode is on (always, in a development build)."""
        current = self._current()
        if current is None:
            return {"known": False, "version": self._version(), "message": UNKNOWN_BUILD}
        return {
            "known": True,
            **_describe(current),
            "title": current.title,
            "version": self._version(),
            "is_dev_build": dev_build.is_development(current),
            "developer_mode": self._developer_mode(current),
        }

    def set_developer_mode(self, on: bool) -> dict:
        """Turn Developer mode on or off; a development build keeps it on whatever is stored."""
        current = self._current()
        if current is None:
            return {"status": "error", "message": UNKNOWN_BUILD}
        settings = read_json(self.settings_path)
        settings[DEVELOPER_MODE_KEY] = bool(on)
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            write_json(self.settings_path, settings)
        except OSError as exc:
            return {"status": "error", "message": f"Couldn't save Developer mode: {exc}"}
        return {"status": "success", "developer_mode": self._developer_mode(current)}

    # ── the newest release ───────────────────────────────────────────────────

    def _stable(self) -> tuple[dev_build.BuildInfo, dev_build.StableRelease | None] | dict:
        current = self._current()
        if current is None:
            return {"status": "error", "message": UNKNOWN_BUILD}
        try:
            entry = self.latest_release(current.repository)
        except ReleasesUnavailable as exc:
            log.error(f"Checking for a release failed: {exc}")
            return {"status": "error", "message": str(exc)}
        return current, None if entry is None else dev_build.stable_release(entry, current.repository)

    def latest_stable(self) -> dict:
        """The newest release and what the device offers for it: an update, a switch from a development
        build, or nothing."""
        found = self._stable()
        if isinstance(found, dict):
            return found
        current, release = found
        return {
            "status": "success",
            "release": None
            if release is None
            else {"version": release.version, "title": release.title, "published_at": release.published_at},
            "offer": dev_build.stable_offer(current, self._version(), release),
        }

    def stable_install_request(self) -> dict:
        """Download the newest release and return the request that installs it. Asked again at install time,
        in case a newer release came out since the check."""
        found = self._stable()
        if isinstance(found, dict):
            return found
        _, release = found
        if release is None:
            return {"status": "error", "message": "No release is published yet."}
        install_type = dev_build.install_type(self._version(), release.version)
        return self._install(dev_build.STABLE_CHANNEL, release.url, dev_build.RELEASE_ASSET, release.sha256, release.version, install_type)

    # ── development builds ───────────────────────────────────────────────────

    def _published(self) -> tuple[dev_build.BuildInfo, list[dev_build.DevRelease]] | dict:
        """The running build and the development builds published now — or an error answer."""
        current = self._current()
        if current is None:
            return {"status": "error", "message": UNKNOWN_BUILD}
        if not self._developer_mode(current):
            return {"status": "error", "message": DEVELOPER_MODE_OFF}
        if not self._plugin_name():
            return {"status": "error", "message": NO_NAME}
        try:
            listing = self.list_releases(current.repository)
        except ReleasesUnavailable as exc:
            log.error(f"Listing development builds failed: {exc}")
            return {"status": "error", "message": str(exc)}
        return current, dev_build.releases(listing, current, self._plugin_name())

    def available_builds(self) -> dict:
        """Every installable development build, marked installed or available."""
        published = self._published()
        if isinstance(published, dict):
            return published
        current, releases = published
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
        """Download the development build published on `channel` right now and return the request that
        installs it. Asked again at install time: a channel's build is replaced on every push, and the
        previous one's download is gone."""
        published = self._published()
        if isinstance(published, dict):
            return published
        _, releases = published
        release = next((r for r in releases if r.info.channel == channel), None)
        if release is None:
            return {"status": "error", "message": f"The {channel} build is no longer published. Check again."}
        name = dev_build.asset_name(self._plugin_name(), release.info)
        answer = self._install(channel, release.url, name, release.sha256, dev_build.dev_label(release), dev_build.DECKY_INSTALL_UPDATE)
        return {**answer, **_describe(release.info)} if answer["status"] == "success" else answer

    # ── downloading ──────────────────────────────────────────────────────────

    def _install(self, channel: str, url: str, name: str, digest: str, label: str, install_type: int) -> dict:
        """Download a build (replacing any earlier download) and check it; the request Decky installs it by."""
        plugin_name = self._plugin_name()
        if not plugin_name:
            return {"status": "error", "message": NO_NAME}
        target = self.downloads_dir / name
        try:
            self.downloads_dir.mkdir(parents=True, exist_ok=True)
            # Earlier builds, and partial files a plugin stopped mid-download left behind.
            for stale in [*self.downloads_dir.glob("*.zip"), *self.downloads_dir.glob("*.part")]:
                stale.unlink()
            self.download(url, target, lambda received, total: self.report(channel, received, total))
        except (ReleasesUnavailable, OSError) as exc:
            log.error(f"Downloading the {channel} build failed: {exc}")
            return {"status": "error", "message": str(exc)}
        if sha256(target) != digest:
            target.unlink(missing_ok=True)
            return {"status": "error", "message": f"The {channel} build did not match its checksum. Try again."}
        return {"status": "success", "install_request": dev_build.install_request(plugin_name, label, digest, str(target), install_type)}


def _describe(info: dev_build.BuildInfo) -> dict:
    return {"channel": info.channel, "commit": info.commit, "short_commit": info.short_commit}
