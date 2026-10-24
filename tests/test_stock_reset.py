"""Resetting a game the original Decky Framegen patched: rules (unit) and the plugin (integration)."""

from __future__ import annotations

import json

import pytest

from conftest import game_file, make_game_dir, run, snapshot, write
from deckyscaler.domain import stock_reset
from deckyscaler.domain.patch_plan import DeleteFile, Move, RemoveTree

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
    # dxgi.dll too: games ship it themselves (mod loaders), and nothing backed it up here.
    assert set(reset.unrecoverable) == {"amd_fidelityfx_dx12.dll", "nvapi64.dll", "dxgi.dll"}
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


OLD_MARKER = json.dumps({"dll_name": "dxgi.dll", "original_launch_options": "mangohud %command%"}).encode()


def test_unpatching_an_older_versions_patch_previews_a_reset_and_resets_once_confirmed(plugin, steam_library):
    root = steam_library.add_game("700", "Old Game", {
        "FRAMEGEN_PATCH": OLD_MARKER, "dxgi.dll": b"old opti", "OptiScaler.ini": b"[x]",
        "libxess.dll": b"old opti xess", "libxess.dll.b": game_file("libxess.dll"),
    })
    other = steam_library.add_game("701", "Other Game", {"libxess.dll": game_file("libxess.dll")})
    patched, other_before = snapshot(root), snapshot(other)

    preview = run(plugin.preview_unpatch_game("700", OURS))

    assert snapshot(root) == patched
    assert preview["status"] == "success" and preview["mode"] == "reset"
    assert preview["evidence"] == stock_reset.MARKER
    assert "libxess.dll" in preview["restore"]
    assert "dxgi.dll" in preview["remove"]
    assert preview["launch_options"] == "mangohud %command%"

    unconfirmed = run(plugin.unpatch_game("700", OURS))
    assert unconfirmed["status"] == "error" and "patched by Decky Framegen" in unconfirmed["message"]
    assert snapshot(root) == patched

    result = run(plugin.unpatch_game("700", OURS, True))

    assert result["status"] == "success"
    assert result["launch_options"] == "mangohud %command%"
    assert sorted(snapshot(root)) == ["Game.exe", "libxess.dll"]
    assert (root / "libxess.dll").read_bytes() == game_file("libxess.dll")
    assert snapshot(other) == other_before


def test_a_game_patched_with_a_record_is_unpatched_by_it_even_when_a_reset_is_confirmed(plugin, plugin_home, steam_library):
    # The device report: a v10 patch puts its libxess under OptiScaler/, so the game's own root
    # libxess.dll has no backup — and the old reset deleted it by name.
    from conftest import NIGHTLY

    root = steam_library.add_game("720", "New Game", {
        "libxess.dll": game_file("libxess.dll"), "amd_fidelityfx_dx12.dll": game_file("amd_fidelityfx_dx12.dll"),
    })
    before = snapshot(root)
    assert run(plugin.patch_game("720", "dxgi.dll", "", NIGHTLY))["status"] == "success"

    preview = run(plugin.preview_unpatch_game("720", OURS))
    result = run(plugin.unpatch_game("720", OURS, True))

    assert preview == {"status": "success", "mode": "record", "name": "New Game", "target_dir": str(root)}
    assert result["status"] == "success"
    assert snapshot(root) == before


def test_an_older_versions_marker_naming_a_path_that_is_gone_resets_the_directory_it_sits_in(plugin, steam_library):
    # The device report: the marker Decky Framegen wrote named a /run/... path that no longer
    # exists, so Unpatch failed with "not found" and Patch was refused.
    stale = json.dumps({"dll_name": "dxgi.dll", "target_dir": "/run/media/gone/Old Game", "original_launch_options": ""})
    root = steam_library.add_game("730", "Old Game", {
        "FRAMEGEN_PATCH": stale.encode(), "dxgi.dll": b"old opti", "libxess.dll.b": game_file("libxess.dll"),
        "libxess.dll": b"old opti xess",
    })

    status = run(plugin.get_game_status("730"))
    preview = run(plugin.preview_unpatch_game("730", OURS))
    result = run(plugin.unpatch_game("730", OURS, True))

    assert status["target_dir"] == str(root)
    assert preview["status"] == "success" and preview["target_dir"] == str(root)
    assert result["status"] == "success"
    assert sorted(snapshot(root)) == ["Game.exe", "libxess.dll"]
    assert (root / "libxess.dll").read_bytes() == game_file("libxess.dll")


def test_a_game_the_plugin_never_touched_is_refused(plugin, steam_library):
    root = steam_library.add_game("710", "Own Opti Game", {"dxgi.dll": b"user's own OptiScaler", "OptiScaler.ini": b"[x]"})
    before = snapshot(root)

    preview = run(plugin.preview_unpatch_game("710", ""))
    result = run(plugin.unpatch_game("710", "", True))

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

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"  # unconfirmed: nothing to undo by record
    assert (game / "libxess.dll.b").exists()
    result = run(plugin.manual_unpatch_directory(str(game), True))

    assert result["status"] == "success"
    assert result["evidence"] == stock_reset.BACKUPS
    assert sorted(path.relative_to(game).as_posix() for path in game.rglob("*")) == [
        "Game.exe", "libxess.dll", "plugins", "plugins/OtherMod.asi"
    ]
    assert (game / "libxess.dll").read_bytes() == game_file("libxess.dll")


@pytest.mark.parametrize("inside", ["", "library"])
def test_the_bundle_itself_is_never_reset(plugin, plugin_home, inside):
    before = snapshot(plugin_home)

    preview = run(plugin.preview_unpatch_directory(str(plugin_home / inside)))
    result = run(plugin.manual_unpatch_directory(str(plugin_home / inside), True))

    assert preview["status"] == result["status"] == "error"
    assert "OptiScaler bundle itself" in result["message"]
    assert snapshot(plugin_home) == before


def test_a_support_file_removed_without_a_backup_is_named_as_maybe_the_games():
    # Games ship XeSS and FidelityFX DLLs themselves; a reset can only remove them by name.
    reset = stock_reset.plan(frozenset({"Game.exe", "FRAMEGEN_PATCH", "dxgi.dll", "libxess.dll"}), frozenset())

    assert "libxess.dll" in reset.unrecoverable


def test_a_reset_that_fails_midway_answers_with_the_error(plugin, tmp_path, monkeypatch):
    from deckyscaler.infrastructure import game_directory

    game = make_game_dir(tmp_path / "games" / "Game", {"dxgi.dll": b"opti", "libxess.dll.b": game_file("libxess.dll")})

    def crash(operations, directory, source):
        raise OSError("device went to sleep")

    monkeypatch.setattr(game_directory, "execute", crash)

    assert run(plugin.manual_unpatch_directory(str(game), True)) == {"status": "error", "message": "device went to sleep"}
