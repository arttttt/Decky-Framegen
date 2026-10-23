"""Resetting a game an earlier plugin version patched: rules (unit) and the plugin (integration)."""

from __future__ import annotations

import pytest

from conftest import game_file, make_game_dir, run, snapshot, write
from framegen.domain import stock_reset
from framegen.domain.patch_plan import DeleteFile, Move, RemoveTree

OURS = "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"

# ── evidence ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        ({"Game.exe", "dxgi.dll", "FRAMEGEN_PATCH", "libxess.dll.b"}, stock_reset.MARKER),
        ({"Game.exe", "dxgi.dll", "libxess.dll.b"}, stock_reset.BACKUPS),
        ({"Game.exe", "nvapi64.dll.b"}, stock_reset.BACKUPS),
        ({"Game.exe", "dxgi.dll", "dlss-enabler.dll"}, stock_reset.LEFTOVERS),
        ({"Game.exe", "fgmod-uninstaller.sh"}, stock_reset.LEFTOVERS),
    ],
)
def test_the_strongest_sign_of_the_plugin_is_the_evidence(entries, expected):
    assert stock_reset.evidence(frozenset(entries)) == expected


@pytest.mark.parametrize(
    "entries",
    [
        {"Game.exe"},
        # What a manual OptiScaler install leaves: nothing proves the plugin was there.
        {"Game.exe", "dxgi.dll", "OptiScaler.ini", "libxess.dll", "fakenvapi.ini", "D3D12_Optiscaler"},
        {"Game.exe", "D3D12_OptiScaler", "OptiScaler"},
        {"Game.exe", "save.b"},
    ],
)
def test_without_evidence_of_the_plugin_nothing_is_planned(entries):
    reset = stock_reset.plan(frozenset(entries), frozenset())

    assert reset == stock_reset.ResetPlan(None, (), (), (), ())


def test_a_marker_kept_in_another_directory_is_evidence_for_the_one_it_names():
    assert stock_reset.evidence(frozenset({"Game.exe", "dxgi.dll"}), marked_elsewhere=True) == stock_reset.MARKER
    assert stock_reset.plan(frozenset({"dxgi.dll"}), frozenset(), marked_elsewhere=True).removed == ("dxgi.dll",)


# ── what a reset does ────────────────────────────────────────────────────────


def test_a_reset_lists_what_it_removes_restores_and_what_may_be_the_games_own():
    entries = frozenset(
        {"Game.exe", "FRAMEGEN_PATCH", "dxgi.dll", "OptiScaler.ini", "libxess.dll", "libxess.dll.b",
         "amd_fidelityfx_dx12.dll", "nvapi64.dll", "plugins"}
    )

    reset = stock_reset.plan(entries, frozenset({"OptiPatcher.asi"}))

    assert reset.evidence == stock_reset.MARKER
    assert reset.restored == ("libxess.dll",)
    assert set(reset.removed) == {
        "FRAMEGEN_PATCH", "dxgi.dll", "OptiScaler.ini", "amd_fidelityfx_dx12.dll", "nvapi64.dll", "plugins"
    }
    assert set(reset.unrecoverable) == {"amd_fidelityfx_dx12.dll", "nvapi64.dll"}
    assert RemoveTree("plugins") in reset.operations
    assert reset.operations[-2:] == (Move("libxess.dll.b", "libxess.dll"), DeleteFile("FRAMEGEN_PATCH"))


def test_a_file_restored_from_its_backup_is_not_reported_as_removed():
    reset = stock_reset.plan(frozenset({"dxgi.dll", "dxgi.dll.b"}), frozenset())

    assert reset.restored == ("dxgi.dll",)
    assert reset.removed == ()
    assert reset.unrecoverable == ()


# ── launch options ───────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("current", "stored", "expected"),
    [
        (OURS, "mangohud %command%", "mangohud %command%"),
        (OURS, "", ""),
        ('WINEDLLOVERRIDES="dxgi=n,b" SteamDeck=0 %command%', "", ""),
        ("~/fgmod/fgmod %command%", "", ""),
        # The user changed them since: not the plugin's to touch.
        ("gamemoderun %command%", "mangohud %command%", None),
        ("", "mangohud %command%", None),
    ],
)
def test_launch_options_go_back_to_the_users_own_only_when_the_plugin_wrote_them(current, stored, expected):
    assert stock_reset.launch_options_after_reset(current, stored) == expected


# ── integration: the plugin, on one game the user picked ─────────────────────


def test_previewing_a_reset_changes_nothing_and_resetting_restores_the_game(plugin, fgmod, steam_library):
    root = steam_library.add_game("700", "Old Game", {"libxess.dll": game_file("libxess.dll")})
    other = steam_library.add_game("701", "Other Game", {"libxess.dll": game_file("libxess.dll")})
    assert run(plugin.patch_game("700", "dxgi.dll", "mangohud %command%", "rdna23-int8"))["status"] == "success"
    assert run(plugin.patch_game("701", "dxgi.dll", "", "rdna23-int8"))["status"] == "success"
    patched, other_before = snapshot(root), snapshot(other)

    preview = run(plugin.preview_reset_game("700", "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"))

    assert snapshot(root) == patched
    assert preview["status"] == "success"
    assert preview["evidence"] == stock_reset.MARKER
    assert "libxess.dll" in preview["restore"]
    assert "dxgi.dll" in preview["remove"]
    assert preview["launch_options"] == "mangohud %command%"

    result = run(plugin.reset_game("700", "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"))

    assert result["status"] == "success"
    assert result["launch_options"] == "mangohud %command%"
    assert sorted(snapshot(root)) == ["Game.exe", "libxess.dll"]
    assert (root / "libxess.dll").read_bytes() == game_file("libxess.dll")
    assert snapshot(other) == other_before


def test_a_game_the_plugin_never_touched_is_refused(plugin, steam_library):
    root = steam_library.add_game("710", "Own Opti Game", {"dxgi.dll": b"user's own OptiScaler", "OptiScaler.ini": b"[x]"})
    before = snapshot(root)

    preview = run(plugin.preview_reset_game("710", ""))
    result = run(plugin.reset_game("710", ""))

    assert preview["status"] == result["status"] == "error"
    assert "nothing to reset" in result["message"]
    assert snapshot(root) == before


def test_a_directory_with_an_old_versions_backups_is_reset(plugin, tmp_path):
    game = make_game_dir(
        tmp_path / "games" / "Wrapper Game",
        {"dxgi.dll": b"opti", "libxess.dll": b"opti xess", "libxess.dll.b": game_file("libxess.dll"),
         "fakenvapi.ini": b"", "OptiScaler.ini": b"[x]"},
    )
    write(game / "plugins" / "OtherMod.asi", game_file("OtherMod.asi"))
    write(game / "plugins" / "OptiPatcher.asi", b"ours")

    result = run(plugin.reset_directory(str(game)))

    assert result["status"] == "success"
    assert result["evidence"] == stock_reset.BACKUPS
    assert sorted(path.relative_to(game).as_posix() for path in game.rglob("*")) == [
        "Game.exe", "libxess.dll", "plugins", "plugins/OtherMod.asi"
    ]
    assert (game / "libxess.dll").read_bytes() == game_file("libxess.dll")
