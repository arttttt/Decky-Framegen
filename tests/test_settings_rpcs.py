"""The settings pages' calls: what they show, and changing global and game settings (integration)."""

from __future__ import annotations

from conftest import NIGHTLY, STABLE, run
from framegen.application import settings as settings_module
from framegen.domain import settings_layers


def setting(answer: dict, section: str, key: str) -> dict:
    sec = next(s for s in answer["sections"] if s["name"] == section)
    return next(x for x in sec["settings"] if x["key"] == key)


def test_global_settings_show_the_newest_versions_keys_with_their_values(plugin, fgmod):
    answer = run(plugin.global_settings())

    assert answer["status"] == "success" and answer["version"] == NIGHTLY
    model = setting(answer, "FSR", "Fsr4Model")
    assert model["kind"] == "enum" and [c["value"] for c in model["choices"]] == ["0", "1", "2", "3"]
    assert (model["value"], model["source"]) == ("auto", settings_layers.DEFAULT)
    assert setting(answer, "Menu", "UseHQFont")["source"] == settings_layers.GLOBAL  # the initial global settings
    assert "FrameGen.FGInput" in answer["unsupported"]  # nukems: 0.9 only


def test_without_a_version_there_is_nothing_to_set(plugin, home):
    assert run(plugin.global_settings())["status"] == "error"


def test_a_global_change_reaches_every_patched_game_but_not_a_games_own(plugin, fgmod, steam_library):
    first = steam_library.add_game("1", "First")
    second = steam_library.add_game("2", "Second")
    run(plugin.patch_game("1", "dxgi.dll", "", NIGHTLY))
    run(plugin.patch_game("2", "dxgi.dll", "", NIGHTLY))
    run(plugin.set_setting("2", "FSR", "Fsr4Model", "0"))

    answer = run(plugin.set_setting("global", "FSR", "Fsr4Model", "1"))

    assert answer == {"status": "success", "skipped": []}
    assert "Fsr4Model=1" in (first / "OptiScaler.ini").read_text()
    assert "Fsr4Model=0" in (second / "OptiScaler.ini").read_text()
    game = run(plugin.game_settings("2"))
    assert (setting(game, "FSR", "Fsr4Model")["value"], setting(game, "FSR", "Fsr4Model")["source"]) == ("0", "game")


def test_clearing_a_games_value_brings_the_global_one_back(plugin, fgmod, steam_library):
    root = steam_library.add_game("1", "Game")
    run(plugin.patch_game("1", "dxgi.dll", "", NIGHTLY))
    run(plugin.set_setting("global", "FSR", "Fsr4Model", "1"))
    run(plugin.set_setting("1", "FSR", "Fsr4Model", "auto"))  # auto for this game, whatever global says
    assert "Fsr4Model=auto" in (root / "OptiScaler.ini").read_text()

    run(plugin.set_setting("1", "FSR", "Fsr4Model", None))

    assert "Fsr4Model=1" in (root / "OptiScaler.ini").read_text()


def test_a_value_the_version_doesnt_take_is_refused(plugin, fgmod, steam_library):
    steam_library.add_game("1", "Game")

    assert run(plugin.set_setting("global", "FSR", "Fsr4Model", "7"))["status"] == "error"
    assert run(plugin.set_setting("1", "FSR", "Nope", "1"))["status"] == "error"


def test_a_game_running_isnt_written(plugin, fgmod, steam_library, monkeypatch):
    root = steam_library.add_game("1", "Game")
    run(plugin.patch_game("1", "dxgi.dll", "", NIGHTLY))
    monkeypatch.setattr(settings_module.processes, "command_lines", lambda: [f"wine {root / 'Game.exe'}"])

    refused = run(plugin.set_setting("1", "FSR", "Fsr4Model", "1"))
    skipped = run(plugin.set_setting("global", "FSR", "Fsr4Model", "1"))

    assert refused["status"] == "error" and "Close the game" in refused["message"]
    assert skipped == {"status": "success", "skipped": ["Game"]}
    assert "Fsr4Model=auto" in (root / "OptiScaler.ini").read_text()
    assert run(plugin.game_settings("1"))["running"] is True


def test_a_game_not_patched_yet_keeps_its_settings_for_the_patch(plugin, fgmod, steam_library):
    root = steam_library.add_game("1", "Game")
    run(plugin.set_setting("1", "FSR", "Fsr4Model", "1"))
    answer = run(plugin.game_settings("1"))
    assert answer["patched"] is False and answer["name"] == "Game"

    run(plugin.patch_game("1", "dxgi.dll", "", NIGHTLY))

    assert "Fsr4Model=1" in (root / "OptiScaler.ini").read_text()


def test_resetting_a_game_follows_the_global_settings_again(plugin, fgmod, steam_library):
    root = steam_library.add_game("1", "Game")
    run(plugin.patch_game("1", "dxgi.dll", "", STABLE))
    run(plugin.set_setting("1", "Menu", "UseHQFont", "true"))
    assert "UseHQFont=true" in (root / "OptiScaler.ini").read_text()

    run(plugin.reset_game_settings("1"))

    assert "UseHQFont=false" in (root / "OptiScaler.ini").read_text()
