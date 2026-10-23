"""Unpacking OptiScaler's .7z archives with the 7-Zip build the plugin ships (tools/7zzs)."""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

SEVEN_ZIP = Path("tools") / "7zzs"
"""The static 7-Zip binary inside the plugin directory (CI adds it to every package)."""


def extract_7z(seven_zip: Path, archive_path: Path, output_dir: Path, members: list[str] | None = None) -> None:
    """Extract an archive (or only `members` of it) into `output_dir`; raises RuntimeError on failure."""
    if not seven_zip.is_file():
        raise RuntimeError(f"7-Zip is missing from this plugin build ({seven_zip}).")
    # Decky unpacks the plugin's zip without keeping file modes, so the binary may lose +x.
    mode = seven_zip.stat().st_mode
    if not mode & stat.S_IXUSR:
        seven_zip.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    output_dir.mkdir(parents=True, exist_ok=True)
    command = [str(seven_zip), "x", "-y", f"-o{output_dir}", str(archive_path), *(members or [])]
    # The build is static; clearing Decky's library path keeps it from picking up Decky's libraries anyway.
    env = {**os.environ, "LD_LIBRARY_PATH": ""}
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError(result.stderr or result.stdout or f"Failed to extract {archive_path.name}")
