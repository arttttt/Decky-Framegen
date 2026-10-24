"""Valve's text KeyValues format (VDF): config.vdf, compatibilitytool.vdf, toolmanifest.vdf."""

from __future__ import annotations

KeyValues = dict[str, "str | KeyValues"]

_ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def _tokens(text: str):
    """Quoted or bare strings and braces, skipping whitespace and // comments."""
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("//", i):
            end = text.find("\n", i)
            i = n if end == -1 else end
        elif c in "{}":
            yield c
            i += 1
        elif c == '"':
            i += 1
            chars: list[str] = []
            while i < n and text[i] != '"':
                if text[i] == "\\" and i + 1 < n:
                    chars.append(_ESCAPES.get(text[i + 1], text[i + 1]))
                    i += 2
                else:
                    chars.append(text[i])
                    i += 1
            i += 1
            yield ("str", "".join(chars))
        else:
            start = i
            while i < n and not text[i].isspace() and text[i] not in '{}"':
                i += 1
            yield ("str", text[start:i])


def parse(text: str) -> KeyValues:
    """The nested key/value tree. Keys are lowercased, as Steam compares them case-insensitively; a key
    given twice keeps the last value. Malformed input yields what was read up to the error."""
    root: KeyValues = {}
    stack = [root]
    key: str | None = None
    for token in _tokens(text):
        if token == "{":
            child: KeyValues = {}
            if key is not None:
                stack[-1][key] = child
            stack.append(child)
            key = None
        elif token == "}":
            if len(stack) > 1:
                stack.pop()
            key = None
        elif key is None:
            key = token[1].lower()
        else:
            stack[-1][key] = token[1]
            key = None
    return root


def find(tree: KeyValues, *path: str) -> str | KeyValues | None:
    """The value at a path of keys (compared case-insensitively), or None when any step is missing."""
    node: str | KeyValues | None = tree
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key.lower())
    return node
