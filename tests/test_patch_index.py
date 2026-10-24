"""Which games use a library version: the index of patched directories follows their markers (integration)."""

from __future__ import annotations

import json

from conftest import NIGHTLY, STABLE, make_game_dir, run
from framegen.infrastructure import game_directory


def test_games_using_a_version_follow_patching_repatching_and_unpatching(plugin, fgmod, steam_library, tmp_path):
    steam_library.add_game("1234", "Test Game")
    manual = make_game_dir(tmp_path / "games" / "Manual")

    run(plugin.patch_game("1234", "dxgi.dll", "", ""))
    run(plugin.manual_patch_directory(str(manual), "dxgi.dll", ""))
    assert run(plugin.library_games_using(STABLE)) == {"status": "success", "games": [str(manual), "Test Game"]}

    run(plugin.patch_game("1234", "dxgi.dll", "", NIGHTLY))
    assert run(plugin.library_games_using(STABLE))["games"] == [str(manual)]
    assert run(plugin.library_games_using(NIGHTLY))["games"] == ["Test Game"]

    run(plugin.manual_unpatch_directory(str(manual)))
    run(plugin.unpatch_game("1234"))
    assert run(plugin.library_games_using(STABLE))["games"] == []
    assert run(plugin.library_games_using(NIGHTLY))["games"] == []
    assert json.loads((fgmod / "patched.json").read_text()) == {}  # the index does not grow with old patches


def test_a_directory_whose_marker_went_another_way_is_not_counted(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", ""))

    (game / "FRAMEGEN_PATCH").unlink()  # e.g. the user deleted the game's files

    assert run(plugin.library_games_using(STABLE))["games"] == []


def test_an_interrupted_patch_still_counts_as_using_its_version(plugin, fgmod, tmp_path, monkeypatch):
    game = make_game_dir(tmp_path / "games" / "Game")

    def crash(operations, directory, source):
        raise OSError("device went to sleep")

    monkeypatch.setattr(game_directory, "execute", crash)
    assert run(plugin.manual_patch_directory(str(game), "dxgi.dll", ""))["status"] == "error"

    assert run(plugin.library_games_using(STABLE))["games"] == [str(game)]


def test_a_read_only_index_never_fails_a_patch(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    (fgmod / "patched.json").mkdir()  # cannot be written as a file

    assert run(plugin.manual_patch_directory(str(game), "dxgi.dll", ""))["status"] == "success"
    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"

