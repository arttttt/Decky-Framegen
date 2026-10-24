"""Edits to OptiScaler.ini, as pure text-to-text transforms.

Each function takes the file's text and returns the new text; reading and
writing the file is the caller's job.
"""

from __future__ import annotations

import re

_SECTION = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")


def set_values(content: str, values: list[tuple[str | None, str, str]]) -> str:
    """Set each (section, key) to its value verbatim, keeping everything else intact.

    An existing key is replaced in place, keeping its line ending. A missing key
    is appended to its section, and a missing section is appended at the end.
    A key without a section is replaced wherever it first appears, else appended.
    """
    if not values:
        return content
    newline = "\r\n" if "\r\n" in content else "\n"
    lines = content.splitlines(keepends=True)

    def line_ending(line: str) -> str:
        if line.endswith("\r\n"):
            return "\r\n"
        return "\n" if line.endswith("\n") else newline

    def ensure_trailing_newline() -> None:
        if lines and not lines[-1].endswith(("\n", "\r")):
            lines[-1] += newline

    def upsert(section: str | None, key: str, value: str) -> None:
        replacement = f"{key}={value}"
        key_pattern = re.compile(rf"^(\s*{re.escape(key)}\s*)=.*$")

        if section is None:
            for idx, line in enumerate(lines):
                if key_pattern.match(line):
                    lines[idx] = f"{replacement}{line_ending(line)}"
                    return
            ensure_trailing_newline()
            lines.append(f"{replacement}{newline}")
            return

        in_section = False
        insert_at = None
        for idx, line in enumerate(lines):
            match = _SECTION.match(line.strip())
            if match:
                if in_section:
                    insert_at = idx
                    break
                if match.group("section") == section:
                    in_section = True
                    continue
            if in_section and key_pattern.match(line):
                lines[idx] = f"{replacement}{line_ending(line)}"
                return

        if in_section:
            if insert_at is None:
                ensure_trailing_newline()
                insert_at = len(lines)
            lines.insert(insert_at, f"{replacement}{newline}")
            return

        ensure_trailing_newline()
        if lines and lines[-1].strip():
            lines.append(newline)
        lines.append(f"[{section}]{newline}")
        lines.append(f"{replacement}{newline}")

    for section, key, value in values:
        upsert(section, key, value)
    return "".join(lines)


_KEY = re.compile(r"^\s*(?P<key>[^=;#\[\s][^=]*?)\s*=")
ENV_PREFIX = "OptiScaler_"


def _normalized_section(name: str) -> str:
    """A section name as an environment variable can spell it: [V-Sync] is VSync."""
    return name.replace("-", "").replace(".", "")


def env_overrides(content: str, environ: dict[str, str]) -> list[tuple[str, str, str]]:
    """The (section, key, value) settings environment variables give an OptiScaler.ini, for keys it
    already has. A variable names its key as `OptiScaler_Section_Key`, `Section_Key` (a section may be
    spelled without `-` and `.`), or a bare `Key` when that key appears in one section only."""
    keys: dict[str, set[str]] = {}
    section = None
    for line in content.splitlines():
        match = _SECTION.match(line.strip())
        if match:
            section = match.group("section")
            keys.setdefault(section, set())
        elif section is not None and (key := _KEY.match(line)):
            keys[section].add(key.group("key"))
    by_spelling = {**{_normalized_section(name): name for name in keys}, **{name: name for name in keys}}
    holders: dict[str, list[str]] = {}
    for name, section_keys in keys.items():
        for key in section_keys:
            holders.setdefault(key, []).append(name)

    def qualified(name: str) -> tuple[str, str] | None:
        spelled, _, key = name.partition("_")
        actual = by_spelling.get(spelled)
        return (actual, key) if actual is not None and key in keys[actual] else None

    settings = []
    for name, value in environ.items():
        if name.startswith(ENV_PREFIX):
            target = qualified(name[len(ENV_PREFIX):])
        else:
            target = qualified(name) if "_" in name else None
            if target is None and len(holders.get(name, [])) == 1:
                target = (holders[name][0], name)
        if target is not None:
            settings.append((*target, value))
    return settings
