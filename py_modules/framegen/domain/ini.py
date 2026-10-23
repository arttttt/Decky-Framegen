"""Edits to OptiScaler.ini, as pure text-to-text transforms.

Each function takes the file's text and returns the new text; reading and
writing the file is the caller's job.
"""

from __future__ import annotations

import re

_SECTION = re.compile(r"^\s*\[(?P<section>[^\]]+)\]\s*$")

# Values the plugin sets in the bundle's OptiScaler.ini at install time, where
# the archive ships them as `auto`.
_BUNDLE_DEFAULTS = (
    # v0.9 split FGType into FGInput/FGOutput; Nukem's mod drives both.
    ("FGInput", "nukems"),
    ("FGOutput", "nukems"),
    ("Fsr4Update", "true"),
    # OptiPatcher ships as an ASI plugin.
    ("LoadAsiPlugins", "true"),
)


def apply_bundle_defaults(content: str) -> str:
    """Replace the archive's `auto` values with the plugin's defaults."""
    for key, value in _BUNDLE_DEFAULTS:
        content = re.sub(rf"{key}\s*=\s*auto", f"{key}={value}", content)
    return disable_hq_font_auto(content)


def disable_hq_font_auto(content: str) -> str:
    """Turn the HQ font auto mode off, which asserts on Proton when its font file is missing."""
    return re.sub(r"UseHQFont\s*=\s*auto", "UseHQFont=false", content)


def migrate_fgtype(content: str) -> str:
    """Rewrite a pre-v0.9-final FGType=X into FGInput=X / FGOutput=X.

    v0.9-final replaced FGType with separate FGInput and FGOutput keys; an INI
    that only has FGType makes the new DLL silently fall back to no frame
    generation. If FGInput is already present, the stale FGType is dropped.
    """
    fg_type = re.search(r"^FGType\s*=\s*(\S+)", content, re.MULTILINE)
    if not fg_type:
        return content
    if re.search(r"^FGInput\s*=", content, re.MULTILINE):
        return re.sub(r"^FGType\s*=\s*\S+\n?", "", content, flags=re.MULTILINE)
    value = fg_type.group(1)
    return re.sub(r"^FGType\s*=\s*\S+", f"FGInput={value}\nFGOutput={value}", content, flags=re.MULTILINE)


def split_override_key(raw_key: str) -> tuple[str | None, str]:
    """`Section.Key` → (section, key); a key without a section → (None, key)."""
    key = str(raw_key).strip()
    if "." in key:
        section, section_key = (part.strip() for part in key.split(".", 1))
        if section and section_key:
            return section, section_key
    return None, key


def apply_overrides(content: str, overrides: dict) -> str:
    """Set each `Section.Key` (or bare `Key`) to its value, keeping everything else intact.

    An existing key is replaced in place, keeping its line ending. A missing key
    is appended to its section, and a missing section is appended at the end.
    A bare key is replaced wherever it first appears, else appended.
    """
    if not overrides:
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

    for raw_key, raw_value in overrides.items():
        section, key = split_override_key(str(raw_key))
        if key:
            upsert(section, key, str(raw_value).strip())
    return "".join(lines)
