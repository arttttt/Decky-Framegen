"""The OptiScaler library: list, install, remove and choose OptiScaler versions on the device."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from framegen.domain import library
from framegen.infrastructure import archive
from framegen.infrastructure.files import sha256
from framegen.infrastructure.github_releases import ReleasesUnavailable
from framegen.infrastructure.library_store import LibraryStore

log = logging.getLogger(__name__)

ListReleases = Callable[[str], list]
Download = Callable[[str, Path, Callable[[int, int | None], None]], None]
Report = Callable[[str, int, int | None], None]
"""Tells the frontend how a download goes: version id, bytes received, total bytes if known."""


def _error(message: str) -> dict:
    return {"status": "error", "message": message}


class Library:
    def __init__(
        self,
        fgmod_path: Path,
        seven_zip: Path,
        list_releases: ListReleases,
        download: Download,
        report: Report,
        refresh_core: Callable[[], None],
        linked_games: Callable[[str], list[str]] = lambda _version_id: [],
    ):
        self.store = LibraryStore(fgmod_path / "library")
        self.seven_zip = seven_zip
        self.list_releases = list_releases
        self.download = download
        self.report = report
        self.refresh_core = refresh_core
        self.linked_games = linked_games
        """The games whose files are symlinks into a version; that version can't be removed while there are any."""
        """Puts the plugin's core and launch scripts into ~/fgmod; every install does it until the patching mechanism settles."""

    def _published(self, channel: str) -> list[library.Available]:
        return library.available(channel, self.list_releases(library.CHANNELS[channel].repository))

    def installed(self) -> dict:
        """The versions games can be patched with, newest first, the default one new patches use,
        and what they take on disk."""
        entries = library.newest_first(self.store.installed())
        sizes = {entry.id: self.store.size(entry.id) for entry in entries}
        default = self.store.default_version()
        return {
            "default": default if any(entry.id == default for entry in entries) else None,
            "versions": [library.choice_json(entry, sizes[entry.id]) for entry in entries],
            "installed_bytes": sum(sizes.values()),
        }

    def versions(self, channel: str) -> dict:
        """A channel's versions: installed ones (also those upstream no longer lists), then the rest."""
        if channel not in library.CHANNELS:
            return _error(f"Unknown channel: {channel}")
        installed = self.store.installed()
        sizes = {entry.id: self.store.size(entry.id) for entry in installed}
        try:
            published = self._published(channel)
            listing_error = None
        except ReleasesUnavailable as exc:
            log.error(f"Listing OptiScaler {channel} releases failed: {exc}")
            published, listing_error = [], str(exc)
        rows = library.catalog(
            [entry for entry in installed if entry.channel == channel], published, self.store.default_version(), sizes
        )
        return {
            "status": "success",
            "versions": [row.__dict__ for row in rows],
            "listing_error": listing_error,
            "installed_bytes": sum(sizes.values()),
        }

    def install(self, channel: str, version_id: str) -> dict:
        """Download, verify, unpack and check a version, then add it to the library in one step.

        Anything that goes wrong leaves the library as it was.
        """
        if channel not in library.CHANNELS:
            return _error(f"Unknown channel: {channel}")
        if any(entry.id == version_id for entry in self.store.installed()):
            return _error(f"{version_id} is already in the library.")
        return self._fetch(channel, version_id, replacing=False)

    def reinstall(self, version_id: str) -> dict:
        """Download a version in the library again and swap it in, for a copy that went bad.

        Anything that goes wrong keeps the copy the library has.
        """
        entry = next((e for e in self.store.installed() if e.id == version_id), None)
        if entry is None:
            return _error(f"{version_id} is not in the library.")
        return self._fetch(entry.channel, version_id, replacing=True)

    def _fetch(self, channel: str, version_id: str, replacing: bool) -> dict:
        try:
            version = next((v for v in self._published(channel) if v.id == version_id), None)
        except ReleasesUnavailable as exc:
            return _error(str(exc))
        if version is None:
            return _error(f"{version_id} is no longer published. Check again.")
        if version.unsupported:
            return _error(f"{version_id} can't be installed: {version.unsupported}.")
        if self.store.free_bytes() < library.space_needed(version.size):
            needed = library.space_needed(version.size) // 1_000_000
            return _error(f"Not enough free space: installing {version_id} needs about {needed} MB.")

        self.store.clear_partial()
        try:
            stage = self.store.staging(version_id)
            archive_path = stage.parent / f"{version_id}.7z"
            self.download(version.url, archive_path, lambda got, total: self.report(version_id, got, total))
            if sha256(archive_path) != version.sha256:
                return _error(f"The {version_id} download did not match its checksum. Try again.")
            files = stage / library.FILES_DIRNAME
            archive.extract_7z(self.seven_zip, archive_path, files)
            family = library.family_of(version.version)
            missing = library.missing_files(family, self.store.files_in(files)) if family else {"a known layout"}
            if missing:
                return _error(f"The {version_id} archive lacks {', '.join(sorted(missing))}; not added.")
            installed = library.entry(version, datetime.now(timezone.utc).isoformat())
            (self.store.replace if replacing else self.store.commit)(stage, installed)
        except (ReleasesUnavailable, RuntimeError, OSError) as exc:
            log.error(f"Installing {version_id} failed: {exc}")
            return _error(f"Installing {version_id} failed: {exc}")
        finally:
            self.store.clear_partial()
        if self.store.default_version() is None:
            self.store.set_default_version(version_id)
        log.info(f"{'Reinstalled' if replacing else 'Installed'} OptiScaler {version_id}")
        message = f"OptiScaler {version.version} is {'downloaded again' if replacing else 'installed'}."
        try:
            self.refresh_core()
        except OSError as exc:
            # The version is in the library either way; only the launch scripts may be stale.
            log.warning(f"Refreshing the core in ~/fgmod after installing {version_id} failed: {exc}")
            message += f" Updating the launch scripts in ~/fgmod failed: {exc}"
        return {"status": "success", "id": version_id, "message": message}

    def remove(self, version_id: str) -> dict:
        default = self.store.default_version()
        refused = library.removal_refused(version_id, {entry.id for entry in self.store.installed()}, default)
        if refused:
            return _error(refused)
        linked = self.linked_games(version_id)
        if linked:
            return _error(f"{', '.join(linked)} use {version_id} through links. Unpatch them first.")
        try:
            self.store.remove(version_id)
        except OSError as exc:
            return _error(f"Removing {version_id} failed: {exc}")
        if default == version_id:
            self.store.set_default_version(None)
        return {"status": "success", "message": f"{version_id} is removed."}

    def set_default(self, version_id: str) -> dict:
        if not any(entry.id == version_id for entry in self.store.installed()):
            return _error(f"{version_id} is not in the library.")
        self.store.set_default_version(version_id)
        return {"status": "success", "default": version_id}
