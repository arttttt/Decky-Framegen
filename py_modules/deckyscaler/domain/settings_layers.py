"""OptiScaler settings in layers: the version's defaults, the user's global settings, and a game's own.

A value is "auto" (OptiScaler's default) unless a layer sets it. Global settings apply to every game and
every OptiScaler version; a game's own settings override them, and a change to a global setting never
touches a game's own. Layers are kept by (section, key), not by version: against a version's schema
(domain/ini_schema) a key it doesn't have, or a value it doesn't accept, is skipped and reported, so a
new nightly needs nothing set again.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .ini_schema import BOOL, ENUM, NUMBER, Section, Setting

AUTO = "auto"
DEFAULT = "default"
GLOBAL = "global"
GAME = "game"

Key = tuple[str, str]
Layer = dict[Key, str]
"""(section, key) → the value a layer sets."""

INITIAL_GLOBAL: Layer = {
    # The HQ font's auto mode asserts on Proton when its font file is missing.
    ("Menu", "UseHQFont"): "false",
    # OptiScaler 0.9's frame generation through Nukem's DLL, and its FSR 4 upgrade; newer versions
    # don't take these values, so they skip them.
    ("FrameGen", "FGInput"): "nukems",
    ("FrameGen", "FGOutput"): "nukems",
    ("FSR", "Fsr4Update"): "true",
}
"""What global settings start as, before the user changes any."""

_INT = re.compile(r"-?\d+|0x[0-9A-Fa-f]+")
_FLOAT = re.compile(r"-?\d+(?:\.\d+)?f?")


def _number(value: str) -> float:
    return float(int(value, 16)) if value.lower().startswith("0x") else float(value.rstrip("fF"))


def accepts(setting: Setting, value: str) -> bool:
    """Whether a value is one a setting takes: "auto", or one its comments allow."""
    if value == AUTO:
        return True
    if "\n" in value or "\r" in value:
        return False
    if setting.kind == BOOL:
        return value in ("true", "false")
    if setting.kind == ENUM:
        return any(choice.value.lower() == value.lower() for choice in setting.choices)
    if setting.kind == NUMBER:
        if not (_INT if setting.integer else _FLOAT).fullmatch(value):
            return False
        number = _number(value)
        return (setting.minimum is None or number >= setting.minimum) and (setting.maximum is None or number <= setting.maximum)
    return True


@dataclass(frozen=True)
class Resolved:
    value: str
    source: str
    """Where the value comes from: DEFAULT ("auto"), GLOBAL or GAME."""


def _schema(sections: tuple[Section, ...]) -> dict[Key, Setting]:
    return {(setting.section, setting.key): setting for section in sections for setting in section.settings}


def resolve(sections: tuple[Section, ...], global_layer: Layer, game_layer: Layer) -> dict[Key, Resolved]:
    """Every setting's value for a game and where it comes from: the game's own, else global, else auto.
    A layer's value the version doesn't accept doesn't count."""
    resolved: dict[Key, Resolved] = {}
    for key, setting in _schema(sections).items():
        if key in game_layer and accepts(setting, game_layer[key]):
            resolved[key] = Resolved(game_layer[key], GAME)
        elif key in global_layer and accepts(setting, global_layer[key]):
            resolved[key] = Resolved(global_layer[key], GLOBAL)
        else:
            resolved[key] = Resolved(AUTO, DEFAULT)
    return resolved


def to_write(sections: tuple[Section, ...], global_layer: Layer, game_layer: Layer) -> list[tuple[str, str, str]]:
    """The (section, key, value) a game's OptiScaler.ini gets: only keys a layer sets, the game's own
    over global. Keys nobody set are left as the file has them."""
    resolved = resolve(sections, global_layer, game_layer)
    return [(section, key, r.value) for (section, key), r in resolved.items() if r.source != DEFAULT]


def unsupported(sections: tuple[Section, ...], layer: Layer) -> list[Key]:
    """The keys a layer sets that a version doesn't have, or with a value it doesn't take."""
    schema = _schema(sections)
    return [key for key, value in layer.items() if key not in schema or not accepts(schema[key], value)]


def layer_json(layer: Layer) -> dict:
    """A layer as stored: {section: {key: value}}."""
    stored: dict[str, dict[str, str]] = {}
    for (section, key), value in sorted(layer.items()):
        stored.setdefault(section, {})[key] = value
    return stored


def parse_layer(data: object) -> Layer:
    """A stored layer; anything that isn't one reads as empty."""
    if not isinstance(data, dict):
        return {}
    return {
        (str(section), str(key)): str(value)
        for section, keys in data.items()
        if isinstance(keys, dict)
        for key, value in keys.items()
        if isinstance(value, (str, int, float, bool))
    }


def view_json(sections: tuple[Section, ...], global_layer: Layer, game_layer: Layer | None = None) -> list[dict]:
    """The schema as a settings page shows it: each setting's value and source, and what it would be
    without the page's own value ("inherited"): global for a game's page (game_layer given), auto for
    the global page."""
    resolved = resolve(sections, global_layer, game_layer or {})
    inherited = resolve(sections, global_layer if game_layer is not None else {}, {})

    def value(key: Key) -> dict:
        return {"value": inherited[key].value, "source": inherited[key].source}

    return [
        {
            "name": section.name,
            "settings": [
                {
                    "key": setting.key,
                    "kind": setting.kind,
                    "description": setting.description,
                    "help": setting.help,
                    "default": setting.default,
                    "choices": [{"value": c.value, "label": c.label} for c in setting.choices],
                    "minimum": setting.minimum,
                    "maximum": setting.maximum,
                    "integer": setting.integer,
                    "value": resolved[(section.name, setting.key)].value,
                    "source": resolved[(section.name, setting.key)].source,
                    "inherited": value((section.name, setting.key)),
                }
                for setting in section.settings
            ],
        }
        for section in sections
    ]


def with_value(layer: Layer, key: Key, value: str | None) -> Layer:
    """A layer with a key set, or cleared with None so the key falls through to the layer below. "auto"
    is a value like any other: a game set to auto ignores a global value for that key."""
    changed = dict(layer)
    if value is None:
        changed.pop(key, None)
    else:
        changed[key] = value
    return changed
