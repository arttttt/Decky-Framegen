"""The settings an OptiScaler.ini offers, read from the file itself: no setting is written down here.

OptiScaler documents every key in the comment block above it: what it does, which values it takes and
its default (every pristine value is "auto", OptiScaler's own default). This module reads those blocks
into a schema, so a new OptiScaler version brings its new settings without a plugin change. The comment
shapes are those of the current nightlies (task-97); a key whose block can't be read as a type is
offered as free text.

Precedence when a block holds several shapes: an int list, then a list of whole numbers, then a word
list, then a range, then a type word, then "true or false" (some keys say "true or false" above a
numbered list by copy and paste), then free text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

BOOL = "bool"
ENUM = "enum"
NUMBER = "number"
TEXT = "text"


@dataclass(frozen=True)
class Choice:
    value: str
    label: str


@dataclass(frozen=True)
class Setting:
    section: str
    key: str
    kind: str
    description: str
    """The block's prose, without the lines that only state values or the default."""
    help: str
    """The whole comment block."""
    default: str | None
    """OptiScaler's default as an ini value; None when the comment states it only in prose."""
    choices: tuple[Choice, ...] = ()
    minimum: float | None = None
    maximum: float | None = None
    integer: bool = False


@dataclass(frozen=True)
class Section:
    name: str
    settings: tuple[Setting, ...]


_SECTION = re.compile(r"^\s*\[(?P<name>[^\]]+)\]\s*$")
_KEY = re.compile(r"^\s*(?P<key>[A-Za-z0-9_.]+)\s*=")
_DASHES = re.compile(r"^-{3,}$")
_DEFAULT = re.compile(r"Default(?: \(auto\))?\s+(?:is\s+(?P<value>.*)|depends\b.*)", re.IGNORECASE)
_DEFAULT_TAIL = re.compile(r"\s+-\s+Default\b.*$|^Default\b.*$", re.IGNORECASE)
_PAIR = re.compile(r"^\s*(?P<value>-?\d+)\s*(?:=|:|-)?\s*(?P<label>\S.*?)\s*$")
_LONE_PAIR = re.compile(r"^\s*(?P<value>-?\d+)\s*(?:=|:|-)\s*(?P<label>\S.*?)\s*$")
_NUMBER = r"-?\d+(?:\.\d+)?f?"
_RANGE = re.compile(
    rf"^(?:From\s+|value range between\s+)?(?P<min>{_NUMBER})\s*(?:to|-|and)\s*(?P<max>{_NUMBER})\b", re.IGNORECASE
)
_OPEN_RANGE = re.compile(
    rf"^(?:integer value above\s*>\s*)?(?P<min>{_NUMBER})\s*(?:to (?:max float value|infinite)|or more)?\b", re.IGNORECASE
)
_WORD = re.compile(r"^(?P<word>[A-Za-z][A-Za-z0-9_]*)(?:\s*\([^)]*\))?$")
_TYPE_WORD = re.compile(r"^(?P<type>float|uint|integer value|string value)\b", re.IGNORECASE)
_BOOL = re.compile(r"\btrue or false\b", re.IGNORECASE)


def _text(line: str) -> str:
    return line.lstrip()[1:].strip()


def _value_part(line: str) -> str:
    """A line without its " - Default …" clause, which carries the default, not the values."""
    return _DEFAULT_TAIL.sub("", line).strip()


def _number(text: str) -> float:
    return float(text.rstrip("fF"))


def _default(lines: list[str]) -> str | None:
    """The default an ini value would hold: the first word after "Default (auto) is", when it is one."""
    for line in lines:
        match = _DEFAULT.search(line)
        if not match:
            continue
        stated = (match.group("value") or "").strip()
        token = re.split(r"[\s,]", stated, maxsplit=1)[0] if stated else ""
        rest = stated[len(token):]
        # A number may trail prose ("0x2D which equals …"); a word is a value only when the statement
        # ends there or goes on after a separator ("rcas", "nofg (…)", "true, …"), else it is prose.
        if re.fullmatch(r"-?\d+(?:\.\d+)?|0x[0-9A-Fa-f]+", token):
            return token
        if rest and not re.match(r"^(?:,|\s\(|\s-\s|\s=\s)", rest):
            return None
        if re.fullmatch(r"true|false", token, re.IGNORECASE):
            return token.lower()
        if re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", token) and token.lower() not in {"off", "disabled", "none", "no", "the"}:
            return token
        return None
    return None


def _int_choices(lines: list[str]) -> tuple[list[Choice], set[int]] | None:
    """A numbered list: "0 = A | 1 = B" (or ":", " - ", "/", "," between pairs), or one pair per line."""
    for index, line in enumerate(lines):
        part = _value_part(line)
        for separator in ("|", " / ", ", "):
            pieces = [p for p in part.split(separator) if p.strip()]
            if len(pieces) < 2:
                continue
            pairs = [_PAIR.match(p) for p in pieces]
            if all(pairs) and all(not re.fullmatch(r"-?\d+(?:\.\d+)?", p.group("label")) for p in pairs):
                return [Choice(p.group("value"), p.group("label")) for p in pairs], {index}
    lone = [(i, _LONE_PAIR.match(_value_part(line))) for i, line in enumerate(lines)]
    run = [(i, m) for i, m in lone if m and not re.fullmatch(r"-?\d+(?:\.\d+)?", m.group("label"))]
    if len(run) >= 2 and all(b[0] == a[0] + 1 for a, b in zip(run, run[1:])):
        return [Choice(m.group("value"), m.group("label")) for _, m in run], {i for i, _ in run}
    return None


def _whole_numbers(lines: list[str]) -> tuple[list[int], bool, int] | None:
    """A list of whole numbers ("2, 4, 8, 16", open with "..."): values, whether it is open, its line."""
    for index, line in enumerate(lines):
        part = _value_part(line)
        open_ended = part.endswith("...")
        numbers = [p.strip() for p in part.rstrip(". ").split(",")]
        if len(numbers) >= 2 and all(re.fullmatch(r"\d+", n) for n in numbers):
            return [int(n) for n in numbers], open_ended, index
    return None


def _words(lines: list[str]) -> tuple[list[str], int] | None:
    """A word list ("nofg, fsrfg, xefg", "rcas, da or lcda", "fsr22 (native DX11), …")."""
    for index, line in enumerate(lines):
        part = _value_part(line)
        if not part or (part == line.strip() and not _next_is_default(lines, index)):
            continue
        pieces = [p.strip() for p in _split_words(part) if p.strip()]
        matches = [_WORD.match(p) for p in pieces]
        words = [m.group("word") for m in matches if m]
        if len(pieces) >= 2 and all(matches) and {w.lower() for w in words} != {"true", "false"}:
            return words, index
    return None


def _split_words(text: str) -> list[str]:
    """A word list split on "," and " or ", but not inside parentheses ("xess (native DX11, Arc only)")."""
    pieces, depth, current, i = [], 0, "", 0
    while i < len(text):
        char = text[i]
        depth += char == "("
        depth -= char == ")"
        if depth == 0 and char == ",":
            pieces.append(current)
            current, i = "", i + 1
            continue
        if depth == 0 and text.startswith(" or ", i):
            pieces.append(current)
            current, i = "", i + 4
            continue
        current += char
        i += 1
    return [*pieces, current]


def _next_is_default(lines: list[str], index: int) -> bool:
    return index + 1 < len(lines) and lines[index + 1].lstrip().lower().startswith("default")


def _range(lines: list[str]) -> tuple[float | None, float | None, bool, int] | None:
    """A numeric range at the start of a line: "0.0 - 2.0", "From 0 to 4", "-1.0 to 1.0", "300.0 or more"."""
    for index, line in enumerate(lines):
        part = _value_part(line)
        match = _RANGE.match(part)
        if match:
            low, high = match.group("min"), match.group("max")
            return _number(low), _number(high), "." not in low + high, index
        opened = _OPEN_RANGE.fullmatch(part) if part != line.strip() else None
        if opened and re.search(r"or more|max float|infinite|above", part, re.IGNORECASE):
            low = opened.group("min")
            return _number(low), None, "." not in low, index
    return None


def _type_word(lines: list[str]) -> tuple[str, int] | None:
    for index, line in enumerate(lines):
        match = _TYPE_WORD.match(line.strip())
        if match and _DEFAULT.search(line):
            return match.group("type").lower(), index
    return None


def _setting(section: str, key: str, block: list[str]) -> Setting:
    lines = [line for line in block if not _DASHES.match(line)]
    help_text = "\n".join(line for line in lines if line)
    default = _default(lines)
    used: set[int] = set()
    kind, choices, minimum, maximum, integer = TEXT, (), None, None, False

    if (numbered := _int_choices(lines)) is not None:
        kind, choices, used = ENUM, tuple(numbered[0]), numbered[1]
        if default is not None and not any(c.value == default for c in choices):
            default = None
    elif (whole := _whole_numbers(lines)) is not None:
        values, open_ended, index = whole
        used = {index}
        if open_ended:
            kind, minimum, integer = NUMBER, float(min(values)), True
        else:
            kind, choices = ENUM, tuple(Choice(str(v), str(v)) for v in values)
    elif (words := _words(lines)) is not None:
        kind, choices, used = ENUM, tuple(Choice(w, w) for w in words[0]), {words[1]}
        if default is not None:
            default = next((c.value for c in choices if c.value.lower() == default.lower()), None)
    elif (span := _range(lines)) is not None:
        kind, minimum, maximum, integer, index = NUMBER, *span
        used = {index}
    elif (typed := _type_word(lines)) is not None:
        word, index = typed
        used = {index}
        if word in {"float", "uint", "integer value"}:
            kind, integer = NUMBER, word != "float"
            minimum = 0.0 if word == "uint" else None
    elif any(_BOOL.search(line) for line in lines):
        kind = BOOL
        used = {i for i, line in enumerate(lines) if _BOOL.search(line)}

    if kind == BOOL and default not in {"true", "false"}:
        default = None
    if kind == NUMBER and default is not None and not re.fullmatch(r"-?\d+(?:\.\d+)?|0x[0-9A-Fa-f]+", default):
        default = None
    if kind == TEXT and default in {"true", "false"}:
        default = None
    description_lines = [
        line for i, line in enumerate(lines) if line and i not in used and not line.lower().startswith("default")
    ]
    return Setting(
        section, key, kind, "\n".join(description_lines), help_text, default, choices, minimum, maximum, integer
    )


def parse(content: str) -> tuple[Section, ...]:
    """Every section of an OptiScaler.ini with the settings its comments describe, in file order.

    A comment block is a run of ";" lines, ended only by an empty line or a section header; it
    describes the key line after it, and the key lines right after that one share it.
    """
    sections: list[Section] = []
    current: str | None = None
    settings: list[Setting] = []
    block: list[str] = []
    shared: list[str] | None = None

    def close() -> None:
        if current is not None:
            sections.append(Section(current, tuple(settings)))

    for raw in content.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        header = _SECTION.match(stripped)
        if header:
            close()
            current, settings, block, shared = header.group("name").strip(), [], [], None
        elif not stripped:
            block, shared = [], None
        elif stripped.startswith(";"):
            block.append(_text(stripped))
            shared = None
        elif (key := _KEY.match(stripped)) and current is not None:
            describing = block if block else (shared or [])
            settings.append(_setting(current, key.group("key"), describing))
            shared, block = describing, []
    close()
    return tuple(section for section in sections if section.settings)
