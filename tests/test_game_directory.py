"""Integration: reading a real game directory for the planner and executing plans on disk."""

from conftest import game_file, write
from framegen.domain import patch_plan as plan
from framegen.infrastructure import game_directory


def test_read_lists_what_is_in_the_directory(tmp_path):
    game = tmp_path / "Game"
    write(game / "dxgi.dll", game_file("dxgi.dll"))
    (game / "plugins").mkdir()

    facts = game_directory.read(game, previous_variant="rdna4-native")

    assert facts == plan.GameDirectory(frozenset({"dxgi.dll", "plugins"}), "rdna4-native")


def test_bundle_files_lists_files_and_directories_relative_to_the_bundle(fgmod, tmp_path):
    files = game_directory.bundle_files(fgmod)

    assert {"OptiScaler.dll", "renames", "renames/dxgi.dll", "plugins/OptiPatcher.asi"} <= files
    assert game_directory.bundle_files(tmp_path / "missing") == frozenset()


def test_execute_carries_out_every_operation_kind(fgmod, tmp_path):
    game = tmp_path / "Game"
    write(game / "keep.dll", b"keep")
    write(game / "old.dll", b"old")
    write(game / "legacy_dir/file", b"x")
    write(game / "legacy_file.ini", b"x")
    write(game / "tree/file", b"x")
    write(game / "plugins/OtherMod.asi", b"other")
    write(game / "OptiScaler.ini", b"[A]\nX=1\n")

    game_directory.execute(
        (
            plan.Move("keep.dll", "keep.dll.b"),
            plan.DeleteFile("old.dll"),
            plan.RemoveFileOrTree("legacy_dir"),
            plan.RemoveFileOrTree("legacy_file.ini"),
            plan.RemoveTree("tree"),
            plan.CopyFromBundle("renames/dxgi.dll", "dxgi.dll"),
            plan.MergeTreeFromBundle("plugins"),
            plan.EditIni("set X", lambda content: content.replace("X=1", "X=2")),
        ),
        game,
        fgmod,
    )

    assert sorted(p.relative_to(game).as_posix() for p in game.rglob("*")) == [
        "OptiScaler.ini",
        "dxgi.dll",
        "keep.dll.b",
        "plugins",
        "plugins/OptiPatcher.asi",
        "plugins/OtherMod.asi",
    ]
    assert (game / "OptiScaler.ini").read_text() == "[A]\nX=2\n"


def test_a_failing_ini_edit_is_logged_and_does_not_abort_the_plan(fgmod, tmp_path, caplog):
    game = tmp_path / "Game"
    write(game / "OptiScaler.ini", b"X=1\n")

    def broken(_content):
        raise ValueError("bad edit")

    game_directory.execute((plan.EditIni("break", broken), plan.DeleteFile("OptiScaler.ini")), game, fgmod)

    assert not (game / "OptiScaler.ini").exists()
    assert "bad edit" in caplog.text
