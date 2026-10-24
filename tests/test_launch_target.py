"""Finding the game directory from a launch command: rules (unit), lookups and the CLI (integration)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, STABLE, game_file, make_game_dir, put_tools_on_path, write
from framegen.application.launch_wrapper import LaunchWrapper, WrapperError
from framegen.domain import launch_target
from framegen.infrastructure import game_locator

# ── unit: rules ──────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("path", "expected"),
    [("/games/Game/Game.exe", "/games/Game"), ("Game.exe", "."), ("/games/Game/", "/games"), ("/", "/")],
)
def test_dirname_behaves_like_the_dirname_command(path, expected):
    assert launch_target.dirname(path) == expected


def test_a_single_argument_is_the_exe_or_the_directory_itself():
    assert launch_target.game_dir_from_command(["/g/Game/Game.exe"]) == "/g/Game"
    assert launch_target.game_dir_from_command(["/g/Game"]) == "/g/Game"


def test_in_a_full_command_the_first_exe_decides():
    command = ["/proton/proton", "waitforexitandrun", "/g/Game/bin/Game.exe", "/g/Game/Other.exe", "-dx12"]

    assert launch_target.game_dir_from_command(command) == "/g/Game/bin"
    assert launch_target.game_dir_from_command(["/proton/proton", "run"]) is None


@pytest.mark.parametrize(
    ("exe", "expected_dir"),
    [
        ("/c/Cyberpunk 2077/REDprelauncher.exe", "/c/Cyberpunk 2077/bin/x64"),
        ("/c/The Witcher 3/REDprelauncher.exe", "/c/The Witcher 3/bin/x64_dx12"),
        ("/c/Baldurs Gate 3/Launcher/LariLauncher.exe", "/c/Baldurs Gate 3/bin"),
        ("/c/HITMAN 3/Launcher.exe", "/c/HITMAN 3/Retail"),
        ("/c/Satisfactory/FactoryGameSteam.exe", "/c/Satisfactory/Engine/Binaries/Win64"),
        ("/c/Unrelated/Launcher.exe", "/c/Unrelated"),
    ],
)
def test_known_launchers_are_remapped_to_the_game_binary(exe, expected_dir):
    assert launch_target.game_dir_from_command(["/proton", exe]) == expected_dir


def test_lutris_id_and_exe_are_read_from_the_command_and_config():
    assert launch_target.lutris_game_id(["env", "lutris:rungameid/42"]) == "42"
    assert launch_target.lutris_game_id(["/g/Game.exe"]) is None
    config = "game:\n  exe: /games/Hades/x64/Hades.exe\n  prefix: /pfx\n"
    assert launch_target.lutris_exe(config) == "/games/Hades/x64/Hades.exe"
    assert launch_target.lutris_exe("game:\n  prefix: /pfx\n") is None


# ── integration: lookups on disk ─────────────────────────────────────────────


def test_unreal_binaries_dir_finds_the_project_binary_outside_engine(tmp_path):
    root = tmp_path / "Game"
    write(root / "Engine" / "Binaries" / "Win64" / "CrashReportClient.exe", b"")
    write(root / "MyGame" / "Binaries" / "Win64" / "MyGame-Win64-Shipping.exe", b"")

    assert game_locator.unreal_binaries_dir(root) == root / "MyGame" / "Binaries" / "Win64"


def test_unreal_binaries_dir_is_none_without_a_project_binary(tmp_path):
    root = tmp_path / "Game"
    write(root / "Engine" / "Binaries" / "Win64" / "CrashReportClient.exe", b"")

    assert game_locator.unreal_binaries_dir(root) is None


@pytest.fixture
def fake_lutris(tmp_path, monkeypatch, home):
    """A `lutris` on PATH listing one game, and that game's YAML config."""
    lutris = f'#!{sys.executable}\nimport json; print(json.dumps([{{"id": 7, "slug": "hades"}}]))\n'
    put_tools_on_path(monkeypatch, tmp_path / "lutris-bin", {"lutris": lutris})
    game = make_game_dir(tmp_path / "lutris-games" / "Hades" / "x64")
    write(home / ".config" / "lutris" / "games" / "Hades-1700000000.yml", f"game:\n  exe: {game}/Game.exe\n".encode())
    return game


def test_lutris_game_dir_resolves_through_lutris_and_the_config(fake_lutris, home):
    assert game_locator.lutris_game_dir("7", home) == fake_lutris
    assert game_locator.lutris_game_dir("8", home) is None


# ── integration: the wrapper service ─────────────────────────────────────────


def test_locate_prefers_lutris_then_falls_back_to_steams_install_path(fake_lutris, home, tmp_path):
    steam_dir = make_game_dir(tmp_path / "steam" / "Game")
    wrapper = LaunchWrapper(home, {"STEAM_COMPAT_INSTALL_PATH": str(steam_dir)})

    assert wrapper.locate(["env", "lutris:rungameid/7"]) == fake_lutris
    assert wrapper.locate(["/proton/proton", "run"]) == steam_dir


def test_locate_follows_unreal_layouts_and_rejects_missing_directories(home, tmp_path):
    root = make_game_dir(tmp_path / "Game")
    write(root / "Engine" / "Content" / "x.pak", b"")
    write(root / "MyGame" / "Binaries" / "Win64" / "MyGame-Win64-Shipping.exe", b"")
    wrapper = LaunchWrapper(home, {})

    assert wrapper.locate([str(root / "Game.exe")]) == root / "MyGame" / "Binaries" / "Win64"
    with pytest.raises(WrapperError, match="Could not resolve game directory!"):
        wrapper.locate([str(tmp_path / "missing" / "Game.exe")])


def test_unpatch_refuses_to_touch_the_bundle_itself(fgmod, home):
    with pytest.raises(WrapperError, match="OptiScaler bundle itself"):
        LaunchWrapper(home, {}).unpatch([str(fgmod)])

    assert (fgmod / "library" / "versions").is_dir()


# ── integration: the CLI the wrappers run ────────────────────────────────────


def run_cli(home: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "framegen", *args],
        env={**os.environ, "HOME": str(home), "PYTHONPATH": str(REPO_ROOT / "py_modules")},
        capture_output=True,
        text=True,
    )


def test_cli_patches_and_unpatches_the_game_a_command_starts(fgmod, home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Cli Game", {"libxess.dll": game_file("libxess.dll")})

    patched = run_cli(home, "patch", "--dll", "winmm.dll", "--", "/proton", str(game / "Game.exe"), "-dx12")
    assert (patched.returncode, patched.stdout.strip()) == (0, str(game))
    assert (game / "winmm.dll").exists()

    unpatched = run_cli(home, "unpatch", "--", str(game / "Game.exe"))
    assert (unpatched.returncode, unpatched.stdout.strip()) == (0, str(game))
    assert sorted(p.name for p in game.iterdir()) == ["Game.exe", "libxess.dll"]


def test_cli_reports_failures_for_the_user_with_exit_code_1(fgmod, home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Cli Game")

    bad_dll = run_cli(home, "patch", "--dll", "d3d11.dll", "--", str(game / "Game.exe"))
    no_game = run_cli(home, "patch", "--", str(tmp_path / "nowhere" / "Game.exe"))
    no_command = run_cli(home, "unpatch")

    assert (bad_dll.returncode, bad_dll.stdout.strip()) == (1, "Invalid proxy DLL name: d3d11.dll")
    assert (no_game.returncode, no_game.stdout.strip()) == (1, "Could not resolve game directory!")
    assert no_command.returncode == 1


def test_cli_reset_ini_replaces_the_games_ini(fgmod, home, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Cli Game", {"OptiScaler.ini": b"[Mine]\nKeep=1\n"})

    run_cli(home, "patch", "--version", STABLE, "--", str(game / "Game.exe"))
    kept = (game / "OptiScaler.ini").read_text()
    run_cli(home, "patch", "--reset-ini", "--", str(game / "Game.exe"))  # keeps the version the game is patched with

    assert "Keep=1" in kept
    # The game's own ini is backed up, and the version's, with the plugin's defaults, takes its place.
    assert (game / "OptiScaler.ini.b").read_text() == "[Mine]\nKeep=1\n"
    assert "FGInput=nukems" in (game / "OptiScaler.ini").read_text()
