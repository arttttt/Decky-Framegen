"""The rules every plan shares, the unpatch of earlier plugin versions' patches, and the launch options to restore."""

from framegen.domain import marker
from framegen.domain import patch_plan as plan
from framegen.domain.patch_plan import Copy, DeleteFile, Move, RemoveFileOrTree, RemoveTree, preserving_existing

# ── keeping what was in the directory ────────────────────────────────────────


def test_a_file_a_copy_would_overwrite_is_backed_up_first():
    operations = preserving_existing((Copy("x.dll", "x.dll"),), frozenset({"x.dll"}))

    assert operations == (Move("x.dll", "x.dll.b"), Copy("x.dll", "x.dll"))


def test_a_file_the_plan_would_delete_is_kept_as_a_backup():
    operations = preserving_existing((DeleteFile("nvngx.dll"),), frozenset({"nvngx.dll"}))

    assert operations == (Move("nvngx.dll", "nvngx.dll.b"),)


def test_a_file_with_a_backup_beside_it_keeps_the_old_behaviour_and_a_backup_is_never_deleted():
    present = frozenset({"version.dll", "version.dll.b", "nvapi64.dll.b"})

    operations = preserving_existing(
        (DeleteFile("version.dll"), DeleteFile("nvapi64.dll.b"), Copy("OptiScaler.dll", "version.dll")), present
    )

    assert operations == (DeleteFile("version.dll"), Copy("OptiScaler.dll", "version.dll"))


def test_files_the_plan_creates_or_moves_are_not_backed_up_again():
    operations = preserving_existing(
        (Move("a.dll", "a.dll.b"), Copy("a.dll", "a.dll"), Copy("new.dll", "new.dll")),
        frozenset({"a.dll"}),
    )

    assert operations == (Move("a.dll", "a.dll.b"), Copy("a.dll", "a.dll"), Copy("new.dll", "new.dll"))


# ── unpatch ──────────────────────────────────────────────────────────────────


def test_unpatch_removes_patch_files_and_restores_backups_over_any_leftover():
    operations = plan.plan_unpatch(
        frozenset({"Game.exe", "dxgi.dll", "libxess.dll", "version.dll", "version.dll.b", "plugins", "fgmod-uninstaller.sh"}),
        frozenset({"OptiPatcher.asi"}),
    )

    assert DeleteFile("dxgi.dll") in operations
    assert DeleteFile("libxess.dll") in operations
    assert RemoveTree("plugins") in operations
    assert DeleteFile("fgmod-uninstaller.sh") in operations
    # version.dll is a proxy name, so it is removed first and the backup then moved back.
    assert operations.index(DeleteFile("version.dll")) < operations.index(Move("version.dll.b", "version.dll"))
    assert all("Game.exe" not in str(op) for op in operations)


def test_unpatch_replaces_a_file_that_still_sits_where_a_backup_is_restored():
    # d3dcompiler_47.dll is not a patch file, so only the restore step can remove it.
    operations = plan.plan_unpatch(frozenset({"d3dcompiler_47.dll", "d3dcompiler_47.dll.b"}), frozenset())

    assert operations == (DeleteFile("d3dcompiler_47.dll"), Move("d3dcompiler_47.dll.b", "d3dcompiler_47.dll"))


def test_unpatch_removes_legacy_artifacts_whether_file_or_directory():
    operations = plan.plan_unpatch(frozenset({"nvngx.ini", "dlss-enabler.log"}), frozenset())

    assert RemoveFileOrTree("nvngx.ini") in operations
    assert RemoveFileOrTree("dlss-enabler.log") in operations


def test_unpatch_removes_only_our_files_from_the_games_own_plugins_directory():
    shared = plan.plan_unpatch(frozenset({"plugins"}), frozenset({"OptiPatcher.asi", "OtherMod.asi"}))
    ours = plan.plan_unpatch(frozenset({"plugins"}), frozenset({"OptiPatcher.asi"}))
    theirs = plan.plan_unpatch(frozenset({"plugins"}), frozenset({"OtherMod.asi"}))

    assert shared == (DeleteFile("plugins/OptiPatcher.asi"),)
    assert ours == (RemoveTree("plugins"),)
    assert theirs == ()


def test_unpatch_restores_a_backed_up_legacy_file_instead_of_deleting_both():
    operations = plan.plan_unpatch(frozenset({"nvapi64.dll", "nvapi64.dll.b"}), frozenset())
    without_backup = plan.plan_unpatch(frozenset({"nvapi64.dll"}), frozenset())

    assert operations == (DeleteFile("nvapi64.dll"), Move("nvapi64.dll.b", "nvapi64.dll"))
    assert without_backup == (RemoveFileOrTree("nvapi64.dll"),)


def test_unpatch_removes_our_marker():
    assert plan.plan_unpatch(frozenset({"Game.exe", "FRAMEGEN_PATCH"}), frozenset()) == (DeleteFile("FRAMEGEN_PATCH"),)


def test_unpatch_of_a_clean_directory_does_nothing():
    assert plan.plan_unpatch(frozenset({"Game.exe", "data"}), frozenset()) == ()


# ── launch options to restore ────────────────────────────────────────────────


def test_original_launch_options_prefer_the_stored_user_options_and_never_keep_ours():
    ours = "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"

    assert marker.original_launch_options("mangohud %command%", "") == "mangohud %command%"
    assert marker.original_launch_options(ours, "gamemoderun %command%") == "gamemoderun %command%"
    assert marker.original_launch_options(ours, ours) == ""
    # Stored options the plugin wrote are not the user's; the current ones are.
    assert marker.original_launch_options("mangohud %command%", ours) == "mangohud %command%"
    assert marker.original_launch_options("", "") == ""
