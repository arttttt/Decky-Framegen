"""Which games use a library version: the index of patched directories follows their markers (integration)."""

from __future__ import annotations

import json

from conftest import NIGHTLY, STABLE, make_game_dir, run


def using(plugin, version_id: str) -> list[str]:
    """The patched games and directories the plugin lists with a version."""
    return [g["name"] for g in run(plugin.patched_games())["games"] if g["version_id"] == version_id]
from deckyscaler.infrastructure import game_directory


def test_games_using_a_version_follow_patching_repatching_and_unpatching(plugin, plugin_home, steam_library, tmp_path):
    steam_library.add_game("1234", "Test Game")
    manual = make_game_dir(tmp_path / "games" / "Manual")

    run(plugin.patch_game("1234", "dxgi.dll", "", STABLE))
    run(plugin.manual_patch_directory(str(manual), "dxgi.dll", STABLE))
    assert sorted(using(plugin, STABLE)) == sorted([str(manual), "Test Game"])

    run(plugin.patch_game("1234", "dxgi.dll", "", NIGHTLY))
    assert using(plugin, STABLE) == [str(manual)]
    assert using(plugin, NIGHTLY) == ["Test Game"]

    run(plugin.manual_unpatch_directory(str(manual)))
    run(plugin.unpatch_game("1234"))
    assert using(plugin, STABLE) == []
    assert using(plugin, NIGHTLY) == []
    assert json.loads((plugin_home / "patched.json").read_text()) == {}  # the index does not grow with old patches


def test_a_directory_whose_marker_went_another_way_is_not_counted(plugin, plugin_home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))

    (game / "DECKYSCALER_PATCH").unlink()  # e.g. the user deleted the game's files

    assert using(plugin, STABLE) == []


def test_an_interrupted_patch_still_counts_as_using_its_version(plugin, plugin_home, tmp_path, monkeypatch):
    game = make_game_dir(tmp_path / "games" / "Game")

    def crash(operations, directory, source):
        raise OSError("device went to sleep")

    monkeypatch.setattr(game_directory, "execute", crash)
    assert run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))["status"] == "error"

    assert using(plugin, STABLE) == [str(game)]


def test_a_read_only_index_never_fails_a_patch(plugin, plugin_home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    (plugin_home / "patched.json").mkdir()  # cannot be written as a file

    assert run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))["status"] == "success"
    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"

