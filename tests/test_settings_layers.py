"""OptiScaler settings in layers: the rules (unit) and where the plugin keeps them (integration)."""

from __future__ import annotations

import pytest

from framegen.domain import ini_schema, settings_layers
from framegen.domain.settings_layers import AUTO, DEFAULT, GAME, GLOBAL, Resolved, accepts
from framegen.infrastructure.settings_store import SettingsStore

INI = """[FrameGen]
; Enables Frame Generation
; true or false - Default (auto) is false
Enabled=auto

; Input
; nofg, fsrfg, xefg - Default (auto) is nofg
FGInput=auto

[FSR]
; Model
; 0 = FP8 | 1 = INT8 | 2 = INT8 Lite
; Default (auto) is the best one the GPU supports
Fsr4Model=auto

; Sharpness
; 0.0 - 1.3 - Default (auto) is 0.3
Sharpness=auto

; Rounding
; integer value - Default (auto) is 1
Rounding=auto

; Font path
TTFFontPath=auto
"""
SCHEMA = ini_schema.parse(INI)
SETTINGS = {(s.section, s.key): s for section in SCHEMA for s in section.settings}


@pytest.mark.parametrize(
    ("key", "value", "accepted"),
    [
        (("FrameGen", "Enabled"), "true", True),
        (("FrameGen", "Enabled"), "yes", False),
        (("FrameGen", "FGInput"), "XeFG", True),  # OptiScaler reads its words whatever their case
        (("FrameGen", "FGInput"), "nukems", False),
        (("FSR", "Fsr4Model"), "1", True),
        (("FSR", "Fsr4Model"), "3", False),
        (("FSR", "Sharpness"), "1.3", True),
        (("FSR", "Sharpness"), "1.4", False),
        (("FSR", "Sharpness"), "-0.1", False),
        (("FSR", "Rounding"), "0x10", True),
        (("FSR", "Rounding"), "1.5", False),
        (("FSR", "TTFFontPath"), "C:\\fonts\\a.ttf", True),
        (("FSR", "TTFFontPath"), "two\nlines", False),
        (("FSR", "Fsr4Model"), AUTO, True),
    ],
)
def test_a_value_is_taken_only_as_the_comments_allow(key, value, accepted):
    assert accepts(SETTINGS[key], value) is accepted


def test_a_games_own_setting_wins_over_global_which_wins_over_auto():
    global_layer = {("FrameGen", "Enabled"): "true", ("FSR", "Fsr4Model"): "1"}
    game_layer = {("FSR", "Fsr4Model"): "0"}

    resolved = settings_layers.resolve(SCHEMA, global_layer, game_layer)

    assert resolved[("FSR", "Fsr4Model")] == Resolved("0", GAME)
    assert resolved[("FrameGen", "Enabled")] == Resolved("true", GLOBAL)
    assert resolved[("FSR", "Sharpness")] == Resolved(AUTO, DEFAULT)


def test_a_global_change_never_reaches_a_games_own_setting():
    game_layer = {("FSR", "Fsr4Model"): "0"}

    for global_value in ("1", "2"):
        written = dict(((s, k), v) for s, k, v in settings_layers.to_write(SCHEMA, {("FSR", "Fsr4Model"): global_value}, game_layer))
        assert written[("FSR", "Fsr4Model")] == "0"


def test_only_what_a_layer_sets_is_written():
    written = settings_layers.to_write(SCHEMA, {("FrameGen", "Enabled"): "true"}, {})

    assert written == [("FrameGen", "Enabled", "true")]


def test_what_a_version_doesnt_have_or_take_is_skipped_and_reported():
    global_layer = {("FrameGen", "FGInput"): "nukems", ("FSR", "Fsr4Update"): "true", ("FrameGen", "Enabled"): "true"}

    assert settings_layers.to_write(SCHEMA, global_layer, {}) == [("FrameGen", "Enabled", "true")]
    assert sorted(settings_layers.unsupported(SCHEMA, global_layer)) == [("FSR", "Fsr4Update"), ("FrameGen", "FGInput")]


def test_a_layer_is_stored_by_section_and_key_and_anything_else_reads_as_empty():
    layer = {("FSR", "Fsr4Model"): "1", ("FrameGen", "Enabled"): "true"}

    assert settings_layers.parse_layer(settings_layers.layer_json(layer)) == layer
    assert settings_layers.layer_json(layer) == {"FSR": {"Fsr4Model": "1"}, "FrameGen": {"Enabled": "true"}}
    assert settings_layers.parse_layer([]) == {}
    assert settings_layers.parse_layer({"FSR": "x"}) == {}


# ── integration: where the plugin keeps them ─────────────────────────────────


def test_global_settings_start_as_the_plugins_and_then_are_the_users(tmp_path):
    store = SettingsStore(tmp_path / "settings")

    assert store.global_layer() == settings_layers.INITIAL_GLOBAL
    store.save_global({("Menu", "UseHQFont"): "true"})

    assert SettingsStore(tmp_path / "settings").global_layer() == {("Menu", "UseHQFont"): "true"}


def test_each_game_keeps_its_own_settings(tmp_path):
    store = SettingsStore(tmp_path / "settings")
    store.save_game("1091500", {("FSR", "Fsr4Model"): "1"})

    assert store.game_layer("1091500") == {("FSR", "Fsr4Model"): "1"}
    assert store.game_layer("730") == {}
    with pytest.raises(ValueError):
        store.game_layer("../escape")


def test_a_value_is_set_or_cleared_and_auto_is_a_value_like_any_other():
    layer = {("FSR", "Fsr4Model"): "1"}

    assert settings_layers.with_value(layer, ("FSR", "Sharpness"), "0.5") == {("FSR", "Fsr4Model"): "1", ("FSR", "Sharpness"): "0.5"}
    assert settings_layers.with_value(layer, ("FSR", "Fsr4Model"), AUTO) == {("FSR", "Fsr4Model"): AUTO}
    assert settings_layers.with_value(layer, ("FSR", "Fsr4Model"), None) == {}
    assert layer == {("FSR", "Fsr4Model"): "1"}  # the layer itself is left as it was


def test_the_pages_get_every_setting_with_its_value_and_source():
    resolved = settings_layers.resolve(SCHEMA, {("FrameGen", "Enabled"): "true"}, {})

    view = settings_layers.view_json(SCHEMA, resolved)

    assert [s["name"] for s in view] == ["FrameGen", "FSR"]
    enabled = view[0]["settings"][0]
    assert (enabled["key"], enabled["kind"], enabled["value"], enabled["source"]) == ("Enabled", "bool", "true", GLOBAL)
    model = view[1]["settings"][0]
    assert model["choices"][1] == {"value": "1", "label": "INT8"} and model["source"] == DEFAULT
