"""Placing a library version in a game directory: the plan (unit) against the real archives' file lists."""

from __future__ import annotations

import pytest

from framegen.domain import ini, library
from framegen.domain.patch_plan import CopyFromBundle, EditIni, Move, PlanError
from framegen.domain.version_placement import Request, is_for_the_game, plan_patch

# The files of the real OptiScaler 0.9.4 and nightly-20261023 archives (7zzs l).
V094 = frozenset({
    "!!.txt", "D3D12_Optiscaler/D3D12Core.dll", "Licenses/DirectX_LICENSE.txt", "Licenses/XeSS_LICENSE.txt",
    "OptiScaler.dll", "OptiScaler.ini", "amd_fidelityfx_dx12.dll", "amd_fidelityfx_framegeneration_dx12.dll",
    "amd_fidelityfx_upscaler_dx12.dll", "amd_fidelityfx_vk.dll", "dlssg_to_fsr3_amd_is_better.dll", "fakenvapi.dll",
    "fakenvapi.ini", "libxell.dll", "libxess.dll", "libxess_dx11.dll", "libxess_fg.dll", "setup_linux.sh",
    "setup_windows.bat",
})
V10 = frozenset({
    "Licenses/DirectX_LICENSE.txt", "OptiScaler.dll", "OptiScaler.ini", "OptiScaler/D3D12_OptiScaler/D3D12Core.dll",
    "OptiScaler/Streamlined_fetcher_windows.bat", "OptiScaler/amd_fidelityfx_upscaler_dx12.dll",
    "OptiScaler/libxess.dll", "OptiScaler/dlssg_to_fsr3_amd_is_better.dll", "setup_linux.sh", "setup_windows.bat",
})


def copies(operations) -> dict[str, str]:
    return {op.destination: op.source for op in operations if isinstance(op, CopyFromBundle)}


def edited_ini(operations, text: str) -> str:
    for op in operations:
        if isinstance(op, EditIni):
            text = op.transform(text)
    return text


def test_v10_mirrors_its_archive_with_the_support_files_in_the_subfolder():
    operations = plan_patch(frozenset({"Game.exe"}), V10, library.FAMILIES["10"], Request("dxgi.dll", "auto"))

    assert copies(operations) == {
        "dxgi.dll": "OptiScaler.dll",
        "OptiScaler.ini": "OptiScaler.ini",
        "OptiScaler/D3D12_OptiScaler/D3D12Core.dll": "OptiScaler/D3D12_OptiScaler/D3D12Core.dll",
        "OptiScaler/amd_fidelityfx_upscaler_dx12.dll": "OptiScaler/amd_fidelityfx_upscaler_dx12.dll",
        "OptiScaler/libxess.dll": "OptiScaler/libxess.dll",
        "OptiScaler/dlssg_to_fsr3_amd_is_better.dll": "OptiScaler/dlssg_to_fsr3_amd_is_better.dll",
    }


def test_0_9_puts_everything_next_to_the_proxy_and_leaves_out_what_is_for_people():
    operations = plan_patch(frozenset({"Game.exe"}), V094, library.FAMILIES["0.9"], Request("winmm.dll", "sdk"))
    placed = copies(operations)

    assert placed["winmm.dll"] == "OptiScaler.dll"
    assert {"libxess.dll", "fakenvapi.ini", "D3D12_Optiscaler/D3D12Core.dll"} <= placed.keys()
    assert not {"!!.txt", "setup_linux.sh", "setup_windows.bat", "Licenses/XeSS_LICENSE.txt", "OptiScaler.dll"} & placed.keys()


@pytest.mark.parametrize("path", ["Licenses/X.txt", "!!.txt", "setup_linux.sh", "OptiScaler/fetch.bat"])
def test_licenses_notes_and_setup_scripts_stay_in_the_archive(path):
    assert not is_for_the_game(path)


def test_the_games_files_are_backed_up_and_only_one_proxy_loads():
    entries = frozenset({"Game.exe", "libxess.dll", "version.dll", "dxgi.dll"})

    operations = plan_patch(entries, V094, library.FAMILIES["0.9"], Request("dxgi.dll", "sdk"))

    assert Move("version.dll", "version.dll.b") in operations  # another proxy would load OptiScaler again
    assert Move("dxgi.dll", "dxgi.dll.b") in operations
    assert operations.index(Move("libxess.dll", "libxess.dll.b")) < operations.index(CopyFromBundle("libxess.dll", "libxess.dll"))


def test_a_fresh_ini_gets_the_familys_defaults_and_the_variant():
    operations = plan_patch(frozenset(), V10, library.FAMILIES["10"], Request("dxgi.dll", "int8"))
    archive_ini = "[FSR]\nFsr4GpuSupport=auto\nFsr4Model=auto\n\n[Menu]\nUseHQFont=auto\n"

    text = edited_ini(operations, archive_ini)

    assert "Fsr4GpuSupport=2" in text and "Fsr4Model=1" in text and "UseHQFont=false" in text


def test_a_kept_ini_only_switches_the_variant_and_forgets_the_previous_one():
    users = "[FSR]\nFsr4GpuSupport=2\nFsr4Model=1\n\n[Menu]\nUseHQFont=true\n"

    operations = plan_patch(frozenset({"OptiScaler.ini"}), V10, library.FAMILIES["10"], Request("dxgi.dll", "auto"))

    assert CopyFromBundle("OptiScaler.ini", "OptiScaler.ini") not in operations
    assert edited_ini(operations, users) == "[FSR]\nFsr4GpuSupport=auto\nFsr4Model=auto\n\n[Menu]\nUseHQFont=true\n"


def test_asking_to_reset_the_ini_backs_up_the_games_and_places_the_versions():
    operations = plan_patch(frozenset({"OptiScaler.ini"}), V10, library.FAMILIES["10"], Request("dxgi.dll", "auto", True))

    assert operations.index(Move("OptiScaler.ini", "OptiScaler.ini.b")) < operations.index(
        CopyFromBundle("OptiScaler.ini", "OptiScaler.ini")
    )


@pytest.mark.parametrize(
    ("files", "request_", "message"),
    [
        (V10, Request("d3d11.dll", "auto"), "Invalid proxy DLL name: d3d11.dll"),
        (V10, Request("dxgi.dll", "sdk"), "OptiScaler 10 has no FSR 4 variant sdk"),
        (V10 - {"OptiScaler.ini"}, Request("dxgi.dll", "auto"), "lacks OptiScaler.ini"),
    ],
)
def test_what_cannot_be_placed_is_refused(files, request_, message):
    with pytest.raises(PlanError, match=message):
        plan_patch(frozenset(), files, library.FAMILIES["10"], request_)


def test_variant_settings_reset_the_other_variants_keys():
    assert library.FAMILIES["10"].variant_settings("int8-lite") == {"FSR.Fsr4GpuSupport": "auto", "FSR.Fsr4Model": "3"}
    assert ini.apply_overrides("[FSR]\nFsr4Model=1\n", library.FAMILIES["10"].variant_settings("auto")) == (
        "[FSR]\nFsr4Model=auto\nFsr4GpuSupport=auto\n"
    )
