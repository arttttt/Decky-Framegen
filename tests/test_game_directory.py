"""Integration: executing plans on disk."""

from conftest import write
from deckyscaler.domain import patch_plan as plan
from deckyscaler.domain import patch_record
from deckyscaler.infrastructure import game_directory


def test_execute_carries_out_every_operation_kind(tmp_path):
    source = tmp_path / "version"
    write(source / "OptiScaler.dll", b"opti")
    write(source / "OptiScaler" / "libxess.dll", b"xess")
    game = tmp_path / "Game"
    write(game / "keep.dll", b"keep")
    write(game / "old.dll", b"old")
    write(game / "legacy_dir/file", b"x")
    write(game / "legacy_file.ini", b"x")
    write(game / "tree/file", b"x")
    write(game / "plugins/OtherMod.asi", b"other")
    write(game / "OptiScaler.ini", b"[A]\nX=1\n")
    (game / "empty").mkdir()

    game_directory.execute(
        (
            plan.Move("keep.dll", "keep.dll.b"),
            plan.DeleteFile("old.dll"),
            plan.RemoveFileOrTree("legacy_dir"),
            plan.RemoveFileOrTree("legacy_file.ini"),
            plan.RemoveTree("tree"),
            plan.Copy("OptiScaler.dll", "dxgi.dll"),
            plan.Copy("OptiScaler/libxess.dll", "OptiScaler/libxess.dll"),
            patch_record.RemoveDirIfEmpty("empty"),
            patch_record.RemoveDirIfEmpty("plugins"),
        ),
        game,
        source,
    )

    assert sorted(p.relative_to(game).as_posix() for p in game.rglob("*")) == [
        "OptiScaler",
        "OptiScaler.ini",
        "OptiScaler/libxess.dll",
        "dxgi.dll",
        "keep.dll.b",
        "plugins",
        "plugins/OtherMod.asi",
    ]
    assert (game / "OptiScaler.ini").read_text() == "[A]\nX=1\n"


def test_a_failing_ini_edit_is_logged_and_leaves_the_file_as_it_was(tmp_path, caplog):
    ini_file = write(tmp_path / "Game" / "OptiScaler.ini", b"X=1\n")

    def broken(_content):
        raise ValueError("bad edit")

    assert game_directory.edit_ini(ini_file, broken, "break") is False
    assert ini_file.read_bytes() == b"X=1\n"
    assert "bad edit" in caplog.text
