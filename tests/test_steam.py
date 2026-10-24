"""Steam library metadata: pure parsing (unit) and discovery on a real filesystem (integration)."""

from pathlib import Path

from conftest import write
from deckyscaler.domain import steam
from deckyscaler.infrastructure import steam as steam_library

LIBRARY_FOLDERS = '''"libraryfolders"
{
\t"0"
\t{
\t\t"path"\t\t"/home/deck/.local/share/Steam"
\t\t"apps"\t\t{ }
\t}
\t"1"
\t{
\t\t"path"\t\t"/run/media/mmcblk0p1"
\t}
}
'''


def manifest(appid: str, name: str, installdir: str) -> str:
    return f'"AppState"\n{{\n\t"appid"\t\t"{appid}"\n\t"name"\t\t"{name}"\n\t"installdir"\t\t"{installdir}"\n}}\n'


# ── unit: parsing and rules ──────────────────────────────────────────────────


def test_parse_library_folders_lists_every_path():
    assert steam.parse_library_folders(LIBRARY_FOLDERS) == ["/home/deck/.local/share/Steam", "/run/media/mmcblk0p1"]


def test_parse_library_folders_unescapes_windows_style_separators():
    assert steam.parse_library_folders('\t"path"\t\t"D:\\\\Games\\\\Steam"\n') == ["D:/Games/Steam"]


def test_parse_app_manifest_reads_appid_name_and_installdir():
    assert steam.parse_app_manifest(manifest("1091500", "Cyberpunk 2077", "Cyberpunk 2077")) == steam.AppManifest(
        "1091500", "Cyberpunk 2077", "Cyberpunk 2077"
    )


def test_parse_app_manifest_leaves_missing_fields_empty():
    assert steam.parse_app_manifest('"AppState"\n{\n\t"appid"\t\t"5"\n}\n') == steam.AppManifest("5", "", "")


def test_is_game_rejects_incomplete_manifests_and_steam_tools():
    assert steam.is_game(steam.AppManifest("1", "Hades", "Hades"))
    assert not steam.is_game(steam.AppManifest("", "Hades", "Hades"))
    assert not steam.is_game(steam.AppManifest("1", "", "Hades"))
    assert not steam.is_game(steam.AppManifest("1493710", "Proton Experimental", "Proton - Experimental"))
    assert not steam.is_game(steam.AppManifest("1628350", "Steam Linux Runtime 3.0 (sniper)", "SteamLinuxRuntime_sniper"))


def test_steam_root_candidates_cover_native_and_flatpak_installs():
    roots = [p.as_posix() for p in steam.steam_root_candidates(Path("/home/deck"))]

    assert "/home/deck/.local/share/Steam" in roots
    assert "/home/deck/.var/app/com.valvesoftware.Steam/home/.local/share/Steam" in roots


# ── integration: discovery on disk ───────────────────────────────────────────


def test_installed_games_spans_native_flatpak_and_extra_libraries(tmp_path):
    home = tmp_path / "home"
    native = home / ".local/share/Steam"
    flatpak = home / ".var/app/com.valvesoftware.Steam/home/.local/share/Steam"
    sd_card = tmp_path / "sdcard"
    write(native / "steamapps/libraryfolders.vdf", f'\t"path"\t\t"{sd_card}"\n'.encode())
    write(native / "steamapps/appmanifest_10.acf", manifest("10", "beta", "Beta").encode())
    write(flatpak / "steamapps/appmanifest_20.acf", manifest("20", "Alpha", "Alpha").encode())
    write(sd_card / "steamapps/appmanifest_30.acf", manifest("30", "Gamma", "Gamma").encode())
    write(sd_card / "steamapps/appmanifest_40.acf", manifest("40", "Proton 9.0", "Proton 9.0").encode())

    games = steam_library.installed_games(home)

    assert [(g.appid, g.name) for g in games] == [("20", "Alpha"), ("10", "beta"), ("30", "Gamma")]
    assert games[2].install_path == sd_card / "steamapps/common/Gamma"
    assert games[2].library_path == sd_card


def test_find_game_and_duplicate_appids_resolve_to_the_last_library(tmp_path):
    home = tmp_path / "home"
    native = home / ".local/share/Steam"
    sd_card = tmp_path / "sdcard"
    write(native / "steamapps/libraryfolders.vdf", f'\t"path"\t\t"{sd_card}"\n'.encode())
    write(native / "steamapps/appmanifest_10.acf", manifest("10", "Moved Game", "Old").encode())
    write(sd_card / "steamapps/appmanifest_10.acf", manifest("10", "Moved Game", "New").encode())

    game = steam_library.find_game(home, "10")

    assert game is not None
    assert game.install_path == sd_card / "steamapps/common/New"
    assert steam_library.find_game(home, "999") is None


def test_executables_finds_exe_files_recursively(tmp_path):
    root = tmp_path / "Game"
    write(root / "Game.exe", b"")
    write(root / "Binaries/Win64/Game-Win64-Shipping.exe", b"")
    write(root / "readme.txt", b"")
    (root / "folder.exe").mkdir()

    found = sorted(p.relative_to(root).as_posix() for p in steam_library.executables(root))

    assert found == ["Binaries/Win64/Game-Win64-Shipping.exe", "Game.exe"]
    assert steam_library.executables(tmp_path / "missing") == []
