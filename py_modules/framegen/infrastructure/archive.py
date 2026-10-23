"""Unpacking release archives with the system `7z`."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def extract_7z(archive_path: Path, output_dir: Path, members: list[str] | None = None) -> None:
    """Extract an archive (or only `members` of it) into `output_dir`; raises RuntimeError on failure."""
    output_dir.mkdir(parents=True, exist_ok=True)
    command = ["7z", "x", "-y", f"-o{output_dir}", str(archive_path), *(members or [])]
    # Decky's bundled libraries on LD_LIBRARY_PATH can break the system 7z.
    env = {**os.environ, "LD_LIBRARY_PATH": ""}
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f"Failed to extract {archive_path.name}")
