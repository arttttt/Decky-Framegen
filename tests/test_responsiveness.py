"""The plugin stays responsive: slow work leaves Decky's event loop free, and status and patching don't
search more than they must (integration)."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

from conftest import STABLE, run
from framegen.application.patcher import Patcher
from framegen.infrastructure import processes
from framegen.infrastructure import steam as steam_dirs


def test_a_slow_status_doesnt_hold_up_another_call(plugin, monkeypatch):
    monkeypatch.setattr(Patcher, "game_status", lambda self, appid: time.sleep(0.5) or {"status": "success"})
    finished: list[str] = []

    async def both():
        async def status():
            await plugin.get_game_status("1")
            finished.append("status")

        async def setup():
            await plugin.launch_setup()
            finished.append("setup")

        await asyncio.gather(status(), setup())

    asyncio.run(both())

    assert finished == ["setup", "status"]


def test_a_patched_games_status_finds_its_marker_through_the_index(plugin, fgmod, steam_library, monkeypatch):
    steam_library.add_game("1234", "Test Game")
    run(plugin.patch_game("1234", "dxgi.dll", "", STABLE))

    def no_search(self, pattern):
        raise AssertionError(f"searched {self} for {pattern}")

    monkeypatch.setattr(Path, "rglob", no_search)

    assert run(plugin.get_game_status("1234"))["patched"] is True


def test_a_game_the_index_doesnt_know_is_still_found_by_searching(plugin, fgmod, steam_library):
    root = steam_library.add_game("1234", "Test Game")
    run(plugin.patch_game("1234", "dxgi.dll", "", STABLE))
    (fgmod / "patched.json").write_text("{}")  # e.g. patched before the index existed

    assert run(plugin.get_game_status("1234"))["target_dir"] == str(root)


def test_patching_scans_the_games_executables_and_processes_once(plugin, fgmod, steam_library, monkeypatch):
    steam_library.add_game("1234", "Test Game")
    calls = {"executables": 0, "processes": 0}
    real_executables, real_command_lines = steam_dirs.executables, processes.command_lines

    def executables(root):
        calls["executables"] += 1
        return real_executables(root)

    def command_lines():
        calls["processes"] += 1
        return real_command_lines()

    monkeypatch.setattr(steam_dirs, "executables", executables)
    monkeypatch.setattr(processes, "command_lines", command_lines)

    assert run(plugin.patch_game("1234", "dxgi.dll", "", STABLE))["status"] == "success"
    assert calls == {"executables": 1, "processes": 1}
