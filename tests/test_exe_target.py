"""Picking the executable (and directory) to patch: rules (unit) and the real process list (integration)."""

import os
from pathlib import Path

from framegen.domain import exe_target
from framegen.infrastructure import processes

ROOT = Path("/games/common/Satisfactory")


def test_normalized_path_maps_wine_paths_onto_linux_ones():
    assert exe_target.normalized_path("Z:\\Games\\Common\\Game.EXE") == "/games/common/game.exe"


def test_unreal_shipping_binary_beats_the_root_launcher():
    shipping = ROOT / "Engine/Binaries/Win64/FactoryGameSteam-Win64-Shipping.exe"
    launcher = ROOT / "FactoryGameSteam.exe"

    target, exe = exe_target.patch_target(ROOT, "Satisfactory", [launcher, shipping], running=None)

    assert exe == shipping
    assert target == shipping.parent


def test_launchers_crash_reporters_and_installers_lose_to_the_game():
    # Same directory and same name match: only the non-game fragment tells them apart.
    game = ROOT / "Game.exe"
    for other in ("GameLauncher.exe", "GameCrashReportClient.exe", "GameSetup.exe", "GameUpdater.exe"):
        assert exe_target.score(game, ROOT, "Game") > exe_target.score(ROOT / other, ROOT, "Game")


def test_name_matching_the_game_or_install_dir_wins():
    named = ROOT / "bin/Satisfactory.exe"
    other = ROOT / "bin/Tool.exe"

    assert exe_target.score(named, ROOT, "Satisfactory") > exe_target.score(other, ROOT, "Satisfactory")


def test_running_executable_matches_wine_command_lines_and_prefers_the_longest_path():
    launcher = Path("/games/Game/Launcher.exe")
    game = Path("/games/Game/bin/x64/Game.exe")
    # A launcher that started the game: both paths appear on one command line.
    lines = ["/usr/bin/bash", "Z:\\games\\Game\\Launcher.exe Z:\\games\\Game\\bin\\x64\\Game.exe -dx12"]

    assert exe_target.running_executable([launcher, game], lines) == game
    short = Path("/games/Game/Game.exe")
    assert exe_target.running_executable([short], ["/usr/bin/bash"]) is None


def test_a_running_executable_decides_the_target_over_scoring():
    running = ROOT / "Launcher/Game.exe"
    shipping = ROOT / "Binaries/Win64/Game-Win64-Shipping.exe"

    assert exe_target.patch_target(ROOT, "Game", [running, shipping], running=running) == (running.parent, running)


def test_a_game_without_executables_is_patched_at_its_root():
    assert exe_target.patch_target(ROOT, "Game", [], running=None) == (ROOT, None)


def test_process_command_lines_include_this_test_process():
    # Integration: the `ps` invocation and its output format work on this OS.
    lines = processes.command_lines()

    assert lines
    assert any("pytest" in line for line in lines), f"pid {os.getpid()} not found"
