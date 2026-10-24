"""A patch places symlinks into the library: patch, unpatch and the library's guard (integration)."""

from __future__ import annotations

import os
import shutil

from conftest import NIGHTLY, STABLE, game_file, make_game_dir, run, snapshot, write


def test_a_linked_patch_points_into_the_library_and_unpatching_restores_the_game(plugin, plugin_home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game", {"libxess.dll": game_file("libxess.dll")})
    before = snapshot(game)
    files = plugin_home / "library" / "versions" / "stable-0.9.4" / "files"

    assert run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))["status"] == "success"

    assert os.readlink(game / "dxgi.dll") == str(files / "OptiScaler.dll")
    assert os.readlink(game / "libxess.dll") == str(files / "libxess.dll")
    assert (game / "libxess.dll.b").read_bytes() == game_file("libxess.dll")
    assert not (game / "OptiScaler.ini").is_symlink()
    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert snapshot(game) == before
    assert (files / "OptiScaler.dll").exists()  # unpatching removes the link, never what it points to


def test_a_link_left_dangling_is_still_removed_on_unpatch(plugin, plugin_home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", NIGHTLY))
    shutil.rmtree(plugin_home / "library" / "versions" / NIGHTLY)

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert sorted(p.name for p in game.iterdir()) == ["Game.exe"]


def test_a_link_the_game_replaced_with_its_own_file_stays(plugin, plugin_home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))
    (game / "libxess.dll").unlink()
    write(game / "libxess.dll", b"the game's update")

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert (game / "libxess.dll").read_bytes() == b"the game's update"
    assert not (game / "dxgi.dll").exists()


def test_a_version_games_are_patched_with_is_not_removed(plugin, plugin_home, steam_library, tmp_path):
    steam_library.add_game("1234", "Linked Game")
    manual = make_game_dir(tmp_path / "games" / "Manual")
    run(plugin.patch_game("1234", "dxgi.dll", "", NIGHTLY))
    run(plugin.manual_patch_directory(str(manual), "dxgi.dll", NIGHTLY))

    removal = run(plugin.library_removal(NIGHTLY))
    refused = run(plugin.library_remove(NIGHTLY))

    reason = f"{manual}, Linked Game are patched with {NIGHTLY}. Unpatch them first."
    assert removal == {"status": "success", "refused": reason}  # told before confirming
    assert refused == {"status": "error", "message": reason}
    run(plugin.unpatch_game("1234"))
    run(plugin.manual_unpatch_directory(str(manual)))
    assert run(plugin.library_remove(NIGHTLY))["status"] == "success"
