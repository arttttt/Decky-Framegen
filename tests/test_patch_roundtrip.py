"""Patch → unpatch round trips on a clean game must leave no trace."""

import asyncio

from conftest import snapshot


def test_fgmod_fixture_is_a_complete_install(plugin, fgmod):
    # Guards the harness itself: if the fixture drifts from the real bundle
    # layout, every other test would be exercising a broken install.
    info = asyncio.run(plugin.check_fgmod_path())

    assert info["exists"] is True
    assert info["selected_fsr4_variant"] == "rdna23-int8"


def test_manual_patch_then_unpatch_restores_clean_game_dir(plugin, fgmod, game_dir):
    before = snapshot(game_dir)

    patched = asyncio.run(plugin.manual_patch_directory(str(game_dir), "dxgi.dll", "rdna23-int8"))
    assert patched["status"] == "success", patched
    assert (game_dir / "dxgi.dll").read_bytes() == (fgmod / "renames" / "dxgi.dll").read_bytes()
    assert (game_dir / "OptiScaler.ini").exists()
    assert (game_dir / "plugins" / "OptiPatcher.asi").exists()

    unpatched = asyncio.run(plugin.manual_unpatch_directory(str(game_dir)))
    assert unpatched["status"] == "success", unpatched
    assert snapshot(game_dir) == before


def test_steam_patch_then_unpatch_restores_game_and_launch_options(plugin, fgmod, steam_library):
    game_root = steam_library.add_game("1234", "Test Game")
    before = snapshot(game_root)
    user_options = "mangohud %command%"

    patched = asyncio.run(plugin.patch_game("1234", "dxgi.dll", user_options, "rdna23-int8"))
    assert patched["status"] == "success", patched
    assert patched["target_dir"] == str(game_root)
    assert patched["launch_options"] == "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"

    status = asyncio.run(plugin.get_game_status("1234"))
    assert status["patched"] is True
    assert status["fsr4_variant"] == "rdna23-int8"

    unpatched = asyncio.run(plugin.unpatch_game("1234"))
    assert unpatched["status"] == "success", unpatched
    assert unpatched["launch_options"] == user_options
    assert snapshot(game_root) == before


def test_path_defaults_point_the_picker_at_home_and_the_native_steam_library(plugin, home):
    defaults = asyncio.run(plugin.get_path_defaults())

    assert defaults == {
        "home": str(home),
        "steam_common": str(home / ".local" / "share" / "Steam" / "steamapps" / "common"),
    }
