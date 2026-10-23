"""Reading a repository's release list from the GitHub API."""

from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.request

API_ROOT = "https://api.github.com"
TIMEOUT_SECONDS = 10


class ReleasesUnavailable(Exception):
    """The release list could not be read; the message says why, for the user."""


def _ssl_context() -> ssl.SSLContext:
    # Decky Loader verifies against certifi's bundle rather than the system paths
    # (helpers.py get_ssl_context, v3.3.0); its plugins run on the same interpreter.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def list_releases(repository: str) -> list:
    """The latest releases of `owner/name`, newest first, as the API returns them (one unauthenticated request)."""
    request = urllib.request.Request(
        f"{API_ROOT}/repos/{repository}/releases?per_page=100",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "Decky-Framegen"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS, context=_ssl_context()) as response:
            listing = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ReleasesUnavailable(f"GitHub answered {exc.code} for {repository} releases") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ReleasesUnavailable(f"Could not reach GitHub: {getattr(exc, 'reason', exc)}") from exc
    except ValueError as exc:
        raise ReleasesUnavailable(f"GitHub sent a release list that is not JSON: {exc}") from exc
    if not isinstance(listing, list):
        raise ReleasesUnavailable("GitHub sent something other than a release list")
    return listing
