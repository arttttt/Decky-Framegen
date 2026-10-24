"""The user's settings in a game's OptiScaler.ini: written on patch, the game's own over global (integration)."""

from __future__ import annotations

from conftest import NIGHTLY, STABLE, make_game_dir, run
from framegen.infrastructure.settings_store import SettingsStore


def ini_of(game) -> str:
    return (game / "OptiScaler.ini").read_text()


def test_a_patch_writes_the_global_settings_the_version_takes(plugin, fgmod, tmp_path):
    SettingsStore(fgmod / "settings").save_global(
        {("FSR", "Fsr4Model"): "1", ("FrameGen", "FGInput"): "nukems", ("Menu", "UseHQFont"): "false"}
    )
    game = make_game_dir(tmp_path / "games" / "Game")

    run(plugin.manual_patch_directory(str(game), "dxgi.dll", NIGHTLY))

    assert "Fsr4Model=1" in ini_of(game)
    assert "FGInput=auto" in ini_of(game)  # nukems: a value this version doesn't take
    assert "UseHQFont=false" in ini_of(game)


def test_a_games_own_setting_wins_over_global(plugin, fgmod, steam_library):
    store = SettingsStore(fgmod / "settings")
    store.save_global({("FSR", "Fsr4Model"): "1"})
    store.save_game("1234", {("FSR", "Fsr4Model"): "0"})
    root = steam_library.add_game("1234", "Test Game")

    run(plugin.patch_game("1234", "dxgi.dll", "", NIGHTLY))

    assert "Fsr4Model=0" in ini_of(root)


def test_a_later_patch_brings_a_changed_global_setting_and_keeps_the_games_own(plugin, fgmod, steam_library):
    store = SettingsStore(fgmod / "settings")
    store.save_game("1234", {("FSR", "Fsr4GpuSupport"): "2"})
    root = steam_library.add_game("1234", "Test Game")
    run(plugin.patch_game("1234", "dxgi.dll", "", NIGHTLY))

    store.save_global({("FSR", "Fsr4GpuSupport"): "1", ("FSR", "Fsr4Model"): "1"})
    run(plugin.patch_game("1234", "dxgi.dll", "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%", NIGHTLY))

    assert "Fsr4GpuSupport=2" in ini_of(root) and "Fsr4Model=1" in ini_of(root)


def test_the_wrapper_brings_the_settings_of_the_game_steam_starts(fgmod, home, tmp_path):
    from framegen.application.launch_wrapper import LaunchWrapper

    store = SettingsStore(fgmod / "settings")
    store.save_game("1234", {("FSR", "Fsr4Model"): "1"})
    game = make_game_dir(tmp_path / "games" / "Wrapped")
    LaunchWrapper(home, {}).patch([str(game / "Game.exe")], "dxgi.dll", NIGHTLY)
    assert "Fsr4Model=auto" in ini_of(game)

    # Already patched the same way: the next start leaves the files, but the settings still go in.
    LaunchWrapper(home, {"SteamAppId": "1234"}).patch([str(game / "Game.exe")], "dxgi.dll")

    assert "Fsr4Model=1" in ini_of(game)


def test_an_ini_the_game_had_before_is_left_as_it_was(plugin, fgmod, tmp_path):
    SettingsStore(fgmod / "settings").save_global({("Menu", "UseHQFont"): "false"})
    game = make_game_dir(tmp_path / "games" / "Own Ini", {"OptiScaler.ini": b"[Menu]\nUseHQFont=true\n"})

    run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))

    assert ini_of(game) == "[Menu]\nUseHQFont=true\n"
