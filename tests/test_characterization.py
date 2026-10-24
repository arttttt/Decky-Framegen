"""Characterization tests: pin down what patch/unpatch does today.

Each scenario records the game directory and the RPC results after every step
and compares them with a golden file. The golden files describe current
behaviour — known defects included — so a refactor can prove it changes
nothing. A deliberate behaviour change (a bug fix) updates its golden file,
and the diff shows exactly what changed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import NIGHTLY, STABLE, game_file, make_game_dir, run, write
from golden import assert_golden, describe_tree, normalize_result


class Recorder:
    """Collects the observable state after each step of a scenario."""

    def __init__(self, tmp_path: Path, watched: Path):
        self.tmp_path = tmp_path
        self.watched = watched
        self.steps: list[dict] = []

    def record(self, step: str, result: dict | None = None) -> None:
        entry: dict = {"step": step, "tree": describe_tree(self.watched)}
        if result is not None:
            entry["result"] = normalize_result(result, self.tmp_path)
        self.steps.append(entry)


# ── Manual directory patching ────────────────────────────────────────────────

# Patches are (proxy DLL, library version).
MANUAL_SCENARIOS = {
    "manual_clean_game": {
        "files": {},
        "patches": [("dxgi.dll", STABLE)],
    },
    # The game ships its own proxy-named DLLs; both get backed up, whichever proxy is used.
    "manual_game_ships_proxy_dlls": {
        "files": {"version.dll": game_file("version.dll"), "dxgi.dll": game_file("dxgi.dll")},
        "patches": [("version.dll", STABLE)],
    },
    # Game-shipped FidelityFX/XeSS/compiler DLLs; those the version also provides are backed up.
    "manual_game_ships_support_dlls": {
        "files": {
            name: game_file(name)
            for name in (
                "libxess.dll",
                "amd_fidelityfx_dx12.dll",
                "amd_fidelityfx_upscaler_dx12.dll",
                "d3dcompiler_47.dll",
            )
        },
        "patches": [("dxgi.dll", STABLE)],
    },
    # User- or game-placed AMD driver DLLs: no version provides them, so they stay.
    "manual_game_ships_driver_dlls": {
        "files": {"amdxcffx64.dll": game_file("amdxcffx64.dll"), "amdxc64.dll": game_file("amdxc64.dll")},
        "patches": [("dxgi.dll", STABLE)],
    },
    # A pre-existing plugins/ folder with someone else's ASI mod.
    "manual_game_has_plugins_dir": {
        "files": {"plugins/OtherMod.asi": game_file("OtherMod.asi")},
        "patches": [("dxgi.dll", STABLE)],
    },
    # Patching twice before unpatching, the second time with a v10 nightly (another family).
    "manual_repatch": {
        "files": {},
        "patches": [("dxgi.dll", STABLE), ("winmm.dll", NIGHTLY)],
    },
    "manual_nightly": {
        "files": {},
        "patches": [("dxgi.dll", NIGHTLY)],
    },
    "manual_asi_proxy": {
        "files": {},
        "patches": [("OptiScaler.asi", STABLE)],
    },
    # An existing per-game INI next to a game-shipped dxgi.dll: both are the game's and stay.
    "manual_existing_old_ini": {
        "files": {
            "OptiScaler.ini": b"[FrameGen]\nFGType=nukems\n\n[Menu]\nUseHQFont=auto\n",
            "dxgi.dll": game_file("dxgi.dll"),
        },
        "patches": [("dxgi.dll", STABLE)],
    },
}


@pytest.mark.parametrize("name", sorted(MANUAL_SCENARIOS))
def test_manual_patch_scenarios(name, plugin, fgmod, tmp_path):
    scenario = MANUAL_SCENARIOS[name]
    game = make_game_dir(tmp_path / "games" / "Game", scenario["files"])
    recorder = Recorder(tmp_path, game)
    recorder.record("initial")

    for dll_name, version in scenario["patches"]:
        result = run(plugin.manual_patch_directory(str(game), dll_name, version))
        recorder.record(f"patch {dll_name} {version}", result)

    result = run(plugin.manual_unpatch_directory(str(game)))
    recorder.record("unpatch", result)

    assert_golden(name, recorder.steps)


def test_manual_patch_rejects_unknown_proxy_name(plugin, fgmod, game_dir):
    result = run(plugin.manual_patch_directory(str(game_dir), "d3d11.dll", STABLE))

    assert result == {"status": "error", "message": "Invalid proxy DLL name: d3d11.dll"}


def test_manual_patch_needs_an_optiscaler_version_in_the_library(plugin, home, game_dir):
    result = run(plugin.manual_patch_directory(str(game_dir), "dxgi.dll", ""))

    assert result == {"status": "error", "message": "No OptiScaler version is downloaded. Download one under OptiScaler versions first."}


def test_a_patch_naming_no_version_keeps_the_games_else_takes_the_newest(plugin, fgmod, game_dir):
    assert run(plugin.manual_patch_directory(str(game_dir), "dxgi.dll", ""))["optiscaler_version"] == NIGHTLY
    run(plugin.manual_patch_directory(str(game_dir), "dxgi.dll", STABLE))

    # The launch wrapper repatches without a version: the game stays on the one the user chose.
    assert run(plugin.manual_patch_directory(str(game_dir), "dxgi.dll", ""))["optiscaler_version"] == STABLE


def test_manual_patch_with_a_version_not_in_the_library_is_refused(plugin, fgmod, game_dir):
    result = run(plugin.manual_patch_directory(str(game_dir), "dxgi.dll", "nightly-20260101"))

    assert result == {"status": "error", "message": "OptiScaler nightly-20260101 is not in the library."}


# ── Steam AppID patching ─────────────────────────────────────────────────────


def test_steam_version_switch_and_status(plugin, fgmod, steam_library, tmp_path):
    root = steam_library.add_game("100", "Version Game")
    recorder = Recorder(tmp_path, root)

    recorder.record("status unpatched", run(plugin.get_game_status("100")))
    recorder.record("patch nightly", run(plugin.patch_game("100", "dxgi.dll", "", NIGHTLY)))
    recorder.record("status nightly", run(plugin.get_game_status("100")))
    recorder.record(
        "repatch stable",
        run(plugin.patch_game("100", "dxgi.dll", "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%", STABLE)),
    )
    recorder.record("status stable", run(plugin.get_game_status("100")))
    recorder.record("unpatch", run(plugin.unpatch_game("100")))

    assert_golden("steam_version_switch_and_status", recorder.steps)


def test_steam_launch_options_survive_repatch(plugin, fgmod, steam_library, tmp_path):
    root = steam_library.add_game("200", "Options Game")
    recorder = Recorder(tmp_path, root)

    recorder.record("patch", run(plugin.patch_game("200", "dxgi.dll", "gamemoderun %command% -dx12", STABLE)))
    # Steam now holds our managed options; a re-patch passes those back in.
    recorder.record(
        "repatch with winmm",
        run(plugin.patch_game("200", "winmm.dll", "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%", STABLE)),
    )
    recorder.record("unpatch", run(plugin.unpatch_game("200")))

    assert_golden("steam_launch_options_survive_repatch", recorder.steps)


def test_steam_target_directory_moves_between_patches(plugin, fgmod, steam_library, tmp_path):
    root = steam_library.add_game("300", "Moving Game")
    recorder = Recorder(tmp_path, root)

    recorder.record("patch at root", run(plugin.patch_game("300", "dxgi.dll", "", STABLE)))
    # A game update adds the real Unreal executable deeper in the tree.
    write(root / "Binaries" / "Win64" / "MovingGame-Win64-Shipping.exe", game_file("MovingGame-Win64-Shipping.exe"))
    recorder.record("game update")
    recorder.record("repatch", run(plugin.patch_game("300", "dxgi.dll", "", STABLE)))
    recorder.record("unpatch", run(plugin.unpatch_game("300")))

    assert_golden("steam_target_directory_moves_between_patches", recorder.steps)


def test_steam_marker_records_the_backed_up_game_files(plugin, fgmod, steam_library):
    root = steam_library.add_game("600", "Xess Game", {"libxess.dll": game_file("libxess.dll")})

    run(plugin.patch_game("600", "dxgi.dll", "", STABLE))

    marker = json.loads((root / "FRAMEGEN_PATCH").read_text())
    assert marker["backed_up_files"] == ["libxess.dll"]
    assert (root / "libxess.dll.b").read_bytes() == game_file("libxess.dll")


def test_steam_unknown_and_unpatched_games(plugin, fgmod, steam_library, tmp_path):
    steam_library.add_game("400", "Untouched Game")
    observed = {
        "status unknown": run(plugin.get_game_status("999")),
        "patch unknown": run(plugin.patch_game("999", "dxgi.dll", "", STABLE)),
        "unpatch unknown": run(plugin.unpatch_game("999")),
        "unpatch never patched": run(plugin.unpatch_game("400")),
        "patch invalid dll": run(plugin.patch_game("400", "d3d11.dll", "", STABLE)),
    }

    assert_golden("steam_unknown_and_unpatched_games", normalize_result(observed, tmp_path))


def test_list_installed_games_skips_proton_and_runtimes(plugin, steam_library, tmp_path):
    steam_library.add_game("500", "Zeta Game")
    steam_library.add_game("501", "alpha game")
    steam_library.add_game("1493710", "Proton Experimental")
    steam_library.add_game("1628350", "Steam Linux Runtime 3.0 (sniper)")

    assert_golden("list_installed_games", run(plugin.list_installed_games()))
