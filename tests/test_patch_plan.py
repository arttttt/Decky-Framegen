"""Unit tests for the pure patch/unpatch planner and the rules beside it."""

import pytest

from framegen.domain import bundle, marker
from framegen.domain import patch_plan as plan
from framegen.domain.patch_plan import CopyFromBundle, DeleteFile, EditIni, MergeTreeFromBundle, Move, RemoveFileOrTree, RemoveTree

BASE_BUNDLE = frozenset(
    {
        "OptiScaler.dll",
        "OptiScaler.ini",
        "renames/dxgi.dll",
        "plugins",
        "D3D12_Optiscaler",
        bundle.FSR4_UPSCALER_FILENAME,
        "fsr4-rdna2-3/amd_fidelityfx_upscaler_dx12.dll",
        *bundle.SUPPORT_FILES,
    }
)


def patch(entries=(), *, bundle_files=BASE_BUNDLE, dll="dxgi.dll", variant="rdna23-int8", **facts):
    game = plan.GameDirectory(frozenset(entries), **facts)
    return plan.plan_patch(game, bundle_files, plan.PatchRequest(dll, variant))


def ops_of(result, kind):
    return [op for op in result.operations if isinstance(op, kind)]


# ── backups and cleanup ──────────────────────────────────────────────────────


def test_a_game_shipped_proxy_dll_is_backed_up_before_ours_is_copied():
    result = patch({"Game.exe", "version.dll"}, dll="dxgi.dll")

    assert Move("version.dll", "version.dll.b") in result.operations


def test_proxy_dlls_are_not_backed_up_in_an_already_patched_directory_or_when_they_are_ours():
    assert not ops_of(patch({"version.dll", "OptiScaler.ini"}), Move)
    assert not ops_of(patch({"dxgi.dll"}, bundled_proxy_copies=frozenset({"dxgi.dll"})), Move)


def test_an_existing_backup_is_never_overwritten():
    result = patch({"version.dll", "version.dll.b"})

    assert Move("version.dll", "version.dll.b") not in result.operations
    assert DeleteFile("version.dll") in result.operations


def test_stale_injectors_and_logs_are_removed():
    result = patch({"nvngx.dll", "OptiScaler.log", "dlss-enabler.dll"})

    assert {DeleteFile("nvngx.dll"), DeleteFile("OptiScaler.log"), DeleteFile("dlss-enabler.dll")} <= set(result.operations)


def test_game_dlls_the_bundle_replaces_are_backed_up():
    result = patch({"amd_fidelityfx_dx12.dll", "d3dcompiler_47.dll"})

    assert Move("amd_fidelityfx_dx12.dll", "amd_fidelityfx_dx12.dll.b") in result.operations
    assert Move("d3dcompiler_47.dll", "d3dcompiler_47.dll.b") in result.operations


@pytest.mark.parametrize("trace", ["OptiScaler.ini", "fakenvapi.dll", "FRAMEGEN_PATCH", "D3D12_Optiscaler"])
def test_in_an_already_patched_directory_our_own_support_dlls_are_replaced_not_backed_up(trace):
    facts = {"managed_support_files": frozenset({"amd_fidelityfx_dx12.dll"})}

    result = patch({"amd_fidelityfx_dx12.dll", trace}, **facts)

    assert DeleteFile("amd_fidelityfx_dx12.dll") in result.operations
    assert not ops_of(result, Move)


def test_in_a_fresh_directory_a_dll_matching_ours_is_still_treated_as_the_games():
    # Without a trace of an earlier patch, an identical file can only have come with the game.
    result = patch({"amd_fidelityfx_dx12.dll"}, managed_support_files=frozenset({"amd_fidelityfx_dx12.dll"}))

    assert Move("amd_fidelityfx_dx12.dll", "amd_fidelityfx_dx12.dll.b") in result.operations


# ── laying down the bundle ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("bundle_files", "variant", "expected"),
    [
        (BASE_BUNDLE, "rdna23-int8", "renames/dxgi.dll"),
        (BASE_BUNDLE - {"renames/dxgi.dll"}, "rdna23-int8", "OptiScaler.dll"),
        (
            BASE_BUNDLE | {"fsr4-rdna2-valve-411-pre10/OptiScaler.dll", "fsr4-rdna2-valve-411-pre10/renames/dxgi.dll"},
            "rdna2-valve-411-pre10",
            "fsr4-rdna2-valve-411-pre10/renames/dxgi.dll",
        ),
        (BASE_BUNDLE | {"fsr4-rdna2-valve-411-pre10/OptiScaler.dll"}, "rdna2-valve-411-pre10", "fsr4-rdna2-valve-411-pre10/OptiScaler.dll"),
    ],
)
def test_the_proxy_dll_comes_from_the_most_specific_injector_available(bundle_files, variant, expected):
    result = patch(bundle_files=bundle_files, variant=variant)

    assert CopyFromBundle(expected, "dxgi.dll") in result.operations


def test_the_users_ini_is_kept_and_edited_otherwise_the_bundle_ini_is_copied():
    kept = patch({"OptiScaler.ini"})
    fresh = patch()

    assert CopyFromBundle("OptiScaler.ini", "OptiScaler.ini") not in kept.operations
    assert CopyFromBundle("OptiScaler.ini", "OptiScaler.ini") in fresh.operations
    assert len(ops_of(kept, EditIni)) == len(ops_of(fresh, EditIni)) == 3


def test_no_ini_edits_when_neither_the_game_nor_the_bundle_has_an_ini():
    assert not ops_of(patch(bundle_files=BASE_BUNDLE - {"OptiScaler.ini"}), EditIni)


def test_variant_overrides_are_written_and_leaving_the_valve_variant_resets_its_keys():
    def overrides_after(variant, previous):
        edit = ops_of(patch({"OptiScaler.ini"}, variant=variant, previous_variant=previous), EditIni)[-1]
        return edit.transform("")

    assert "Fsr4ForceModel=2" in overrides_after("rdna2-valve-411-pre10", "")
    assert "Fsr4ForceModel=auto" in overrides_after("rdna23-int8", "rdna2-valve-411-pre10")
    assert "LoadCustomAmdxc64OnRdna2=false" in overrides_after("rdna23-int8", "rdna2-valve-411-pre10")
    assert overrides_after("rdna23-int8", "rdna4-native") == ""


def test_support_files_upscaler_and_variant_extras_are_copied():
    bundle_files = BASE_BUNDLE | {
        "fsr4-rdna3-4-official-411/amd_fidelityfx_upscaler_dx12.dll",
        "fsr4-rdna3-4-official-411/amdxcffx64.dll",
    }

    result = patch(bundle_files=bundle_files, variant="rdna34-official-411")

    assert {MergeTreeFromBundle("plugins"), MergeTreeFromBundle("D3D12_Optiscaler")} <= set(result.operations)
    assert CopyFromBundle("libxess.dll", "libxess.dll") in result.operations
    assert result.upscaler_source == "fsr4-rdna3-4-official-411/amd_fidelityfx_upscaler_dx12.dll"
    assert CopyFromBundle("fsr4-rdna3-4-official-411/amdxcffx64.dll", "amdxcffx64.dll") in result.operations


def test_the_active_upscaler_is_used_when_the_variant_copy_is_missing():
    assert patch(variant="rdna4-native").upscaler_source == bundle.FSR4_UPSCALER_FILENAME


@pytest.mark.parametrize(
    ("missing", "message"),
    [
        ({"OptiScaler.dll"}, "OptiScaler.dll not found in ~/fgmod. Reinstall OptiScaler."),
        (
            {bundle.FSR4_UPSCALER_FILENAME, "fsr4-rdna2-3/amd_fidelityfx_upscaler_dx12.dll"},
            "FSR4 upscaler variant not found for rdna23-int8. Reinstall OptiScaler.",
        ),
    ],
)
def test_an_incomplete_bundle_is_refused_before_anything_changes(missing, message):
    with pytest.raises(plan.PlanError, match=message.replace(".", r"\.")):
        patch(bundle_files=BASE_BUNDLE - missing)


# ── unpatch ──────────────────────────────────────────────────────────────────


def test_unpatch_removes_patch_files_and_restores_backups_over_any_leftover():
    operations = plan.plan_unpatch(
        frozenset({"Game.exe", "dxgi.dll", "libxess.dll", "version.dll", "version.dll.b", "plugins", "fgmod-uninstaller.sh"})
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
    operations = plan.plan_unpatch(frozenset({"d3dcompiler_47.dll", "d3dcompiler_47.dll.b"}))

    assert operations == (DeleteFile("d3dcompiler_47.dll"), Move("d3dcompiler_47.dll.b", "d3dcompiler_47.dll"))


def test_unpatch_removes_legacy_artifacts_whether_file_or_directory():
    operations = plan.plan_unpatch(frozenset({"nvngx.ini", "dlss-enabler.log"}))

    assert RemoveFileOrTree("nvngx.ini") in operations
    assert RemoveFileOrTree("dlss-enabler.log") in operations


def test_unpatch_of_a_clean_directory_does_nothing():
    assert plan.plan_unpatch(frozenset({"Game.exe", "data"})) == ()


# ── variant detection and launch options to restore ──────────────────────────


def test_detect_variant_requires_every_extra_file_to_match():
    official = bundle.FSR4_VARIANTS["rdna34-official-411"]
    extra = official["extra_files"][0]

    assert bundle.detect_variant(official["sha256"], {extra["name"]: extra["sha256"]}) == "rdna34-official-411"
    # Same upscaler without the driver override: the plain SDK variant.
    assert bundle.detect_variant(official["sha256"], {}) == "rdna4-native"
    assert bundle.detect_variant(official["sha256"], {extra["name"]: "0" * 64}) == "rdna4-native"
    assert bundle.detect_variant("f" * 64, {}) is None


def test_detect_variant_rejects_a_partial_match_of_a_multi_file_variant():
    valve = bundle.FSR4_VARIANTS["rdna2-valve-411-pre10"]
    first, second = valve["extra_files"]

    assert bundle.detect_variant(valve["sha256"], {first["name"]: first["sha256"], second["name"]: second["sha256"]}) == (
        "rdna2-valve-411-pre10"
    )
    assert bundle.detect_variant(valve["sha256"], {first["name"]: first["sha256"]}) != "rdna2-valve-411-pre10"
    assert bundle.detect_variant(None, {}) is None


def test_original_launch_options_prefer_the_stored_user_options_and_never_keep_ours():
    ours = "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"

    assert marker.original_launch_options("mangohud %command%", "") == "mangohud %command%"
    assert marker.original_launch_options(ours, "gamemoderun %command%") == "gamemoderun %command%"
    assert marker.original_launch_options(ours, ours) == ""
    # Stored options the plugin wrote are not the user's; the current ones are.
    assert marker.original_launch_options("mangohud %command%", ours) == "mangohud %command%"
    assert marker.original_launch_options("", "") == ""
