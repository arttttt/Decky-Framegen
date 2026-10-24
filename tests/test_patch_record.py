"""The patch record: what a patch did, written first, and undone exactly (unit + integration)."""

from __future__ import annotations

import json

import pytest

from conftest import STABLE, game_file, make_game_dir, run, snapshot, write
from framegen.domain import patch_record
from framegen.domain.patch_plan import Copy, DeleteFile, EditIni, Move
from framegen.domain.patch_record import Backup, PatchRecord, Placed, RemoveDirIfEmpty
from framegen.infrastructure import game_directory

HASHES = {
    "OptiScaler.dll": "a" * 64,
    "OptiScaler.ini": "b" * 64,
    "libxess.dll": "c" * 64,
    "plugins/OptiPatcher.asi": "d" * 64,
    "D3D12_Optiscaler/D3D12Core.dll": "e" * 64,
}

# ── unit: recording a plan ───────────────────────────────────────────────────


def test_a_plan_is_recorded_as_placed_files_backups_and_created_directories():
    operations = (
        Move("libxess.dll", "libxess.dll.b"),
        DeleteFile("nvngx.ini"),
        Copy("OptiScaler.dll", "dxgi.dll"),
        Copy("OptiScaler.ini", "OptiScaler.ini"),
        EditIni("x", lambda text: text),
        Copy("plugins/OptiPatcher.asi", "plugins/OptiPatcher.asi"),
        Copy("D3D12_Optiscaler/D3D12Core.dll", "D3D12_Optiscaler/D3D12Core.dll"),
        Copy("libxess.dll", "libxess.dll"),
    )

    recorded = patch_record.record(operations, frozenset({"Game.exe", "libxess.dll", "plugins"}), HASHES)

    assert recorded == PatchRecord(
        placed=(
            Placed("dxgi.dll", "a" * 64),
            Placed("OptiScaler.ini", None),  # OptiScaler rewrites its ini; it is ours whatever it holds
            Placed("plugins/OptiPatcher.asi", "d" * 64),
            Placed("D3D12_Optiscaler/D3D12Core.dll", "e" * 64),
            Placed("libxess.dll", "c" * 64),
        ),
        backups=(Backup("libxess.dll", "libxess.dll.b"),),
        # plugins/ was the game's own; D3D12_Optiscaler/ is the patch's.
        created_dirs=("D3D12_Optiscaler",),
    )


def test_the_record_round_trips_through_the_marker_and_old_markers_have_none():
    recorded = PatchRecord((Placed("dxgi.dll", "a" * 64), Placed("OptiScaler.ini", None)), (Backup("x", "x.b"),), ("d",))
    marker = {"dll_name": "dxgi.dll", **patch_record.to_json(recorded, complete=True)}

    assert patch_record.parse(json.loads(json.dumps(marker))) == recorded
    assert marker["complete"] is True
    assert patch_record.parse({"dll_name": "dxgi.dll", "backed_up_files": []}) is None
    assert patch_record.parse({"format": 2, "placed": "garbage"}) is None
    assert patch_record.parse({**marker, "format": 1}) is None


# ── unit: undoing a record ───────────────────────────────────────────────────

RECORD = PatchRecord(
    placed=(Placed("dxgi.dll", "a" * 64), Placed("libxess.dll", "c" * 64), Placed("OptiScaler.ini", None),
            Placed("D3D12_Optiscaler/D3D12Core.dll", "e" * 64)),
    backups=(Backup("libxess.dll", "libxess.dll.b"),),
    created_dirs=("D3D12_Optiscaler",),
)


def test_undoing_removes_what_was_placed_restores_backups_and_drops_the_marker_last():
    current = {"dxgi.dll": "a" * 64, "libxess.dll": "c" * 64, "OptiScaler.ini": "f" * 64,
               "D3D12_Optiscaler/D3D12Core.dll": "e" * 64, "libxess.dll.b": "9" * 64}

    assert patch_record.plan_unpatch(RECORD, current) == (
        DeleteFile("dxgi.dll"),
        DeleteFile("libxess.dll"),
        DeleteFile("OptiScaler.ini"),
        DeleteFile("D3D12_Optiscaler/D3D12Core.dll"),
        Move("libxess.dll.b", "libxess.dll"),
        RemoveDirIfEmpty("D3D12_Optiscaler"),
        DeleteFile("FRAMEGEN_PATCH"),
    )


def test_a_backup_comes_back_over_a_file_put_there_since():
    current = {"dxgi.dll": "a" * 64, "libxess.dll": "1" * 64, "libxess.dll.b": "9" * 64}

    operations = patch_record.plan_unpatch(RECORD, current)

    assert operations.index(DeleteFile("libxess.dll")) < operations.index(Move("libxess.dll.b", "libxess.dll"))


def test_a_file_put_there_since_stays_when_nothing_was_backed_up_for_it():
    current = {"dxgi.dll": "a" * 64, "D3D12_Optiscaler/D3D12Core.dll": "1" * 64}

    operations = patch_record.plan_unpatch(RECORD, current)

    assert DeleteFile("D3D12_Optiscaler/D3D12Core.dll") not in operations


def test_files_and_backups_already_gone_are_skipped():
    operations = patch_record.plan_unpatch(RECORD, {"dxgi.dll": "a" * 64})

    assert operations == (DeleteFile("dxgi.dll"), RemoveDirIfEmpty("D3D12_Optiscaler"), DeleteFile("FRAMEGEN_PATCH"))


# ── integration: the plugin ──────────────────────────────────────────────────


def test_patching_writes_the_record_and_unpatching_restores_the_game_exactly(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game", {"libxess.dll": game_file("libxess.dll")})
    before = snapshot(game)

    assert run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))["status"] == "success"
    marker = json.loads((game / "FRAMEGEN_PATCH").read_text())
    assert marker["format"] == 2 and marker["complete"] is True
    assert {"path": "dxgi.dll", "sha256": marker["placed"][0]["sha256"]} in marker["placed"]
    assert marker["backups"] == [{"original": "libxess.dll", "backup": "libxess.dll.b"}]

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert snapshot(game) == before


def test_an_interrupted_patch_can_still_be_undone(plugin, fgmod, tmp_path, monkeypatch):
    game = make_game_dir(tmp_path / "games" / "Game", {"libxess.dll": game_file("libxess.dll")})
    before = snapshot(game)
    real_execute = game_directory.execute

    def crash_halfway(operations, directory, fgmod_path):
        real_execute(operations[: len(operations) // 2], directory, fgmod_path)
        raise OSError("device went to sleep")

    monkeypatch.setattr(game_directory, "execute", crash_halfway)
    assert run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))["status"] == "error"
    assert json.loads((game / "FRAMEGEN_PATCH").read_text())["complete"] is False
    monkeypatch.setattr(game_directory, "execute", real_execute)

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert snapshot(game) == before


def test_unpatching_restores_the_backup_over_a_file_put_there_after_patching(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game", {"libxess.dll": game_file("libxess.dll")})
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))
    (game / "libxess.dll").unlink()  # replacing the file; writing through the link would change the library
    write(game / "libxess.dll", b"someone's own libxess")

    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    # The directory goes back to how it was before the patch: what came after is its owner's to track.
    assert (game / "libxess.dll").read_bytes() == game_file("libxess.dll")
    assert not (game / "libxess.dll.b").exists()
    assert not (game / "dxgi.dll").exists()


def test_a_failed_unpatch_keeps_the_marker_and_says_so(plugin, fgmod, tmp_path, monkeypatch):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))
    real_execute = game_directory.execute

    def fail_before_the_end(operations, directory, fgmod_path):
        real_execute(operations[:2], directory, fgmod_path)
        raise PermissionError("read-only file system")

    monkeypatch.setattr(game_directory, "execute", fail_before_the_end)
    result = run(plugin.manual_unpatch_directory(str(game)))

    assert result == {"status": "error", "message": "Permission error while unpatching: read-only file system"}
    assert (game / "FRAMEGEN_PATCH").exists()
    monkeypatch.setattr(game_directory, "execute", real_execute)
    assert run(plugin.manual_unpatch_directory(str(game)))["status"] == "success"
    assert sorted(p.name for p in game.iterdir()) == ["Game.exe"]


@pytest.mark.parametrize("action", ["unpatch", "patch"])
def test_a_game_patched_by_an_older_version_is_left_alone(plugin, fgmod, tmp_path, action):
    old_marker = json.dumps({"dll_name": "dxgi.dll", "backed_up_files": ["libxess.dll"]}).encode()
    game = make_game_dir(tmp_path / "games" / "Game", {"FRAMEGEN_PATCH": old_marker, "dxgi.dll": b"old opti"})
    before = snapshot(game)

    if action == "unpatch":
        result = run(plugin.manual_unpatch_directory(str(game)))
    else:
        result = run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))

    assert result == {"status": "error", "message": "This game was patched by an older version of the plugin. "
                                                     "Unpatch it first: the plugin shows what that removes."}
    assert snapshot(game) == before


def test_a_steam_game_patched_by_an_older_version_says_so_and_keeps_its_launch_options(plugin, steam_library):
    old_marker = json.dumps({"dll_name": "dxgi.dll", "original_launch_options": "mangohud %command%"}).encode()
    root = steam_library.add_game("800", "Old Steam Game", {"FRAMEGEN_PATCH": old_marker, "dxgi.dll": b"old opti"})
    before = snapshot(root)

    status = run(plugin.get_game_status("800"))
    result = run(plugin.unpatch_game("800"))

    assert status["patched"] is True and "older version of the plugin" in status["message"]
    assert result["status"] == "error" and "launch_options" not in result
    assert snapshot(root) == before


@pytest.mark.parametrize("reset_ini", [False, True])
def test_a_repatch_keeps_the_users_ini_settings_unless_asked_to_reset_them(plugin, fgmod, tmp_path, reset_ini):
    from framegen.application.patcher import Patcher

    game = make_game_dir(tmp_path / "games" / "Game")
    patcher = Patcher(tmp_path / "home")
    patcher.patch_directory(game, "dxgi.dll")
    write(game / "OptiScaler.ini", (game / "OptiScaler.ini").read_bytes() + b"\n[Mine]\nKeep=1\n")

    assert patcher.patch_directory(game, "dxgi.dll", reset_ini=reset_ini)["status"] == "success"

    assert (b"Keep=1" in (game / "OptiScaler.ini").read_bytes()) is not reset_ini
    # Either way the ini is the patch's, and unpatching removes it.
    assert patcher.unpatch_directory(game)["status"] == "success"
    assert sorted(p.name for p in game.iterdir()) == ["Game.exe"]


def test_unpatching_a_directory_with_a_record_needs_no_confirmation(plugin, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Game")
    run(plugin.manual_patch_directory(str(game), "dxgi.dll", STABLE))

    assert run(plugin.preview_unpatch_directory(str(game))) == {"status": "success", "mode": "record", "target_dir": str(game)}


def test_a_patched_game_whose_marker_names_a_stale_path_still_reads_as_patched(plugin, fgmod, steam_library):
    root = steam_library.add_game("740", "Moved Game")
    run(plugin.patch_game("740", "dxgi.dll", "", STABLE))
    marker_path = root / "FRAMEGEN_PATCH"
    marker_path.write_text(json.dumps({**json.loads(marker_path.read_text()), "target_dir": "/run/media/gone/Moved Game"}))

    status = run(plugin.get_game_status("740"))

    assert status["patched"] is True and status["target_dir"] == str(root)


def test_a_patch_is_intact_while_everything_it_placed_is_there_as_placed():
    whole = {"dxgi.dll": "a" * 64, "libxess.dll": "c" * 64, "OptiScaler.ini": "rewritten by OptiScaler",
             "D3D12_Optiscaler/D3D12Core.dll": "e" * 64}

    assert patch_record.intact(RECORD, whole)
    assert not patch_record.intact(RECORD, {k: v for k, v in whole.items() if k != "dxgi.dll"})
    assert not patch_record.intact(RECORD, {**whole, "libxess.dll": "1" * 64})
    assert not patch_record.intact(RECORD, {k: v for k, v in whole.items() if k != "OptiScaler.ini"})


def test_a_marker_describes_a_finished_patch_of_this_version_under_this_name():
    from framegen.domain import marker

    details = {"complete": True, "optiscaler_version": "nightly-1", "dll_name": "dxgi.dll", "placement": "link"}

    assert marker.describes(details, "nightly-1", "dxgi.dll")
    assert not marker.describes({**details, "complete": False}, "nightly-1", "dxgi.dll")
    assert not marker.describes(details, "nightly-2", "dxgi.dll")
    assert not marker.describes(details, "nightly-1", "winmm.dll")
    assert not marker.describes({**details, "placement": "copy"}, "nightly-1", "dxgi.dll")
