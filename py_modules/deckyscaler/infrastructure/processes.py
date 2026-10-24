"""The command lines of running processes."""

from __future__ import annotations

import logging
import subprocess

log = logging.getLogger(__name__)


def command_lines() -> list[str]:
    """One command line per running process; empty when `ps` cannot be run."""
    try:
        result = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, check=False)
    except OSError as exc:
        log.error(f"[DeckyScaler] running exe scan failed: {exc}")
        return []
    return result.stdout.splitlines()
