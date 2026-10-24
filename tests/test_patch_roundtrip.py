"""Patch → unpatch round trips on a clean game must leave no trace."""

import asyncio

from conftest import NIGHTLY, STABLE, snapshot


def test_the_fixture_has_both_optiscaler_families(plugin, fgmod):
    # Guards the harness itself: every other test patches with this library.
    assert [v["id"] for v in asyncio.run(plugin.library_installed())["versions"]] == [NIGHTLY, STABLE]


def test_manual_patch_then_unpatch_restores_clean_game_dir(plugin, fgmod, game_dir):
    before = snapshot(game_dir)

    patched = asyncio.run(plugin.manual_patch_directory(str(game_dir), "dxgi.dll", STABLE))
    assert patched["status"] == "success", patched
    version_files = fgmod / "library" / "versions" / "stable-0.9.4" / "files"
    assert (game_dir / "dxgi.dll").read_bytes() == (version_files / "OptiScaler.dll").read_bytes()
    assert (game_dir / "OptiScaler.ini").exists()

    unpatched = asyncio.run(plugin.manual_unpatch_directory(str(game_dir)))
    assert unpatched["status"] == "success", unpatched
    assert snapshot(game_dir) == before


def test_steam_patch_then_unpatch_restores_game_and_launch_options(plugin, fgmod, steam_library):
    game_root = steam_library.add_game("1234", "Test Game")
    before = snapshot(game_root)
    user_options = "mangohud %command%"

    patched = asyncio.run(plugin.patch_game("1234", "dxgi.dll", user_options, STABLE))
    assert patched["status"] == "success", patched
    assert patched["target_dir"] == str(game_root)
    assert patched["launch_options"] == "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"

    status = asyncio.run(plugin.get_game_status("1234"))
    assert status["patched"] is True
    assert status["optiscaler_version"] == "stable-0.9.4"

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


def test_a_first_patch_without_the_games_launch_options_is_refused_and_changes_nothing(plugin, fgmod, steam_library):
    root = steam_library.add_game("1234", "Test Game")
    before = snapshot(root)

    result = asyncio.run(plugin.patch_game("1234", "dxgi.dll", None, STABLE))

    assert result["status"] == "error" and "launch options" in result["message"]
    assert snapshot(root) == before


def test_a_repatch_without_the_games_launch_options_keeps_the_stored_ones(plugin, fgmod, steam_library):
    steam_library.add_game("1234", "Test Game")
    asyncio.run(plugin.patch_game("1234", "dxgi.dll", "mangohud %command%", STABLE))

    repatched = asyncio.run(plugin.patch_game("1234", "dxgi.dll", None, STABLE))
    unpatched = asyncio.run(plugin.unpatch_game("1234"))

    assert repatched["original_launch_options"] == "mangohud %command%"
    assert unpatched["launch_options"] == "mangohud %command%"


def test_the_plugin_serves_the_launch_setup(plugin):
    setup = asyncio.run(plugin.launch_setup())

    assert setup["default"] == "dxgi.dll" and setup["wrapper"]["patch"] == "~/fgmod/fgmod %command%"


def test_path_defaults_follow_a_flatpak_steam(plugin, home):
    flatpak_steamapps = home / ".var" / "app" / "com.valvesoftware.Steam" / "home" / ".local" / "share" / "Steam" / "steamapps"
    flatpak_steamapps.mkdir(parents=True)

    assert asyncio.run(plugin.get_path_defaults())["steam_common"] == str(flatpak_steamapps / "common")
