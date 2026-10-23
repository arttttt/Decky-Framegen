"""Facts about a GitHub release asset that both the library and development builds rely on."""

from __future__ import annotations

import re

_SHA256_DIGEST = re.compile(r"^sha256:([0-9a-f]{64})$")


def sha256(asset: dict) -> str | None:
    """The asset's sha256 from GitHub's `digest` ("sha256:<hex>"); None when it has no usable one."""
    match = _SHA256_DIGEST.match(str(asset.get("digest", "")))
    return match.group(1) if match else None
