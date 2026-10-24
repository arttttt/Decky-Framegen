"""Small filesystem helpers shared by the services."""

from __future__ import annotations

import filecmp
import hashlib
import json
from collections.abc import Callable
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def files_match(file_a: Path, file_b: Path) -> bool:
    """True when both files exist and have identical content."""
    try:
        return file_a.exists() and file_b.exists() and filecmp.cmp(file_a, file_b, shallow=False)
    except OSError:
        return False


def read_json(path: Path) -> dict:
    """The JSON object stored at `path`, or {} when it is missing, unreadable or not an object."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def rewrite_text(path: Path, transform: Callable[[str], str]) -> bool:
    """Apply `transform` to a text file's content; write it back only if it changed.

    Returns whether the file changed.
    """
    # newline="": the text keeps its own line endings both ways (OptiScaler.ini ships with CRLF).
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        content = f.read()
    updated = transform(content)
    if updated == content:
        return False
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(updated)
    return True
