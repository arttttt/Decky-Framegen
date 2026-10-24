"""Experimental placement by symlinks into the library: patch, unpatch and the library's guard (integration)."""

from __future__ import annotations

import os
import shutil

from conftest import NIGHTLY, game_file, make_game_dir, run, snapshot, write


def test_a_linked_patch_points_into_the_library_and_unpatching_restores_the_game(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game", {"libxess.dll": game_file("libxess.dll")})
    before = snapshot(game)
    files = fgmod / "library" / "versions" / "stable-0.9.4" / "files"

    patched = run(plugin.manual_patch_directory(str(game), "dxgi.dll", "", True))

    assert patched["status"] == "success"
    assert patched["message"] == f"OptiScaler 0.9.4 is linked from the library into {game}."  # the user sees how it went

    assert os.readlink(game / "dxgi.dll") == str(files / "OptiScaler.dll")
    assert os.readlink(game / "libxess.dll") == str(files / "libxess.dll")
    assert (game / "libxess.dll.b").read_bytes() == game_file("libxess.dll")
    assert not (game / "OptiScaler.ini").is_symlink()
    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert snapshot(game) == before
    assert (files / "OptiScaler.dll").exists()  # unpatching removes the link, never what it points to


def test_a_link_left_dangling_is_still_removed_on_unpatch(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", NIGHTLY, True))
    shutil.rmtree(fgmod / "library" / "versions" / NIGHTLY)

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert sorted(p.name for p in game.iterdir()) == ["Game.exe"]


def test_a_link_the_game_replaced_with_its_own_file_stays(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", "", True))
    (game / "libxess.dll").unlink()
    write(game / "libxess.dll", b"the game's update")

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert (game / "libxess.dll").read_bytes() == b"the game's update"
    assert not (game / "dxgi.dll").exists()


def test_a_version_games_are_linked_to_is_not_removed(plugin, fgmod, steam_library, tmp_path):
    steam_library.add_game("1234", "Linked Game")
    copied = make_game_dir(tmp_path / "games" / "Copied")
    run(plugin.patch_game("1234", "dxgi.dll", "", NIGHTLY, True))
    run(plugin.manual_patch_directory(str(copied), "dxgi.dll", NIGHTLY))

    removal = run(plugin.library_removal(NIGHTLY))
    refused = run(plugin.library_remove(NIGHTLY))
    status = run(plugin.get_game_status("1234"))

    reason = f"Linked Game use {NIGHTLY} through links. Unpatch them first."
    assert removal == {"status": "success", "refused": reason, "games": [str(copied), "Linked Game"]}  # told before confirming
    assert refused == {"status": "error", "message": reason}
    assert status["linked"] is True
    run(plugin.unpatch_game("1234"))
    assert run(plugin.library_remove(NIGHTLY))["status"] == "success"  # a copy-patched game doesn't hold it
