"""Reading a repository's releases from GitHub: the list, and an asset's file."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request
from collections.abc import Callable
from pathlib import Path

API_ROOT = "https://api.github.com"
TIMEOUT_SECONDS = 10
DOWNLOAD_TIMEOUT_SECONDS = 120


class ReleasesUnavailable(Exception):
    """The release list or a release asset could not be read; the message says why, for the user."""


def _ssl_context() -> ssl.SSLContext:
    # Decky Loader verifies against certifi's bundle rather than the system paths
    # (helpers.py get_ssl_context, v3.3.0); its plugins run on the same interpreter.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _get_json(url: str, subject: str, kind: str) -> object:
    request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "DeckyScaler"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=_ssl_context()) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ReleasesUnavailable(f"GitHub answered {exc.code} for {subject}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ReleasesUnavailable(f"Could not reach GitHub: {getattr(exc, 'reason', exc)}") from exc
    except ValueError as exc:
        raise ReleasesUnavailable(f"GitHub sent {kind} that is not JSON: {exc}") from exc


def list_releases(repository: str) -> list:
    """The latest releases of `owner/name`, newest first, as the API returns them (one unauthenticated request)."""
    listing = _get_json(f"{API_ROOT}/repos/{repository}/releases?per_page=100", f"{repository} releases", "a release list")
    if not isinstance(listing, list):
        raise ReleasesUnavailable("GitHub sent something other than a release list")
    return listing


def latest_release(repository: str) -> dict | None:
    """The release GitHub marks latest for `owner/name` (never a prerelease or draft), or None when there is
    none yet (one unauthenticated request)."""
    try:
        release = _get_json(f"{API_ROOT}/repos/{repository}/releases/latest", f"{repository}'s latest release", "a release")
    except ReleasesUnavailable as exc:
        if isinstance(exc.__cause__, urllib.error.HTTPError) and exc.__cause__.code == 404:
            return None
        raise
    if not isinstance(release, dict):
        raise ReleasesUnavailable("GitHub sent something other than a release")
    return release


CHUNK_BYTES = 64 * 1024

Progress = Callable[[int, int | None], None]
"""Bytes received so far, and the total when the server said it."""


def download(url: str, destination: Path, on_progress: Progress | None = None) -> None:
    """Save a release asset to `destination`, replacing it only once the whole file has arrived."""
    partial = destination.with_name(destination.name + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "DeckyScaler"})
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS, context=_ssl_context()) as response:
            length = response.headers.get("Content-Length")
            total = int(length) if length and length.isdigit() else None
            received = 0
            with open(partial, "wb") as out:
                while chunk := response.read(CHUNK_BYTES):
                    out.write(chunk)
                    received += len(chunk)
                    if on_progress:
                        on_progress(received, total)
        partial.replace(destination)
    except urllib.error.HTTPError as exc:
        raise ReleasesUnavailable(f"GitHub answered {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ReleasesUnavailable(f"Could not download {url}: {getattr(exc, 'reason', exc)}") from exc
    finally:
        partial.unlink(missing_ok=True)
