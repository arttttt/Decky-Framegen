"""Placing a library version in a game directory: the plan (unit) against the real archives' file lists."""

from __future__ import annotations

import pytest

from framegen.domain import library
from framegen.domain.patch_plan import Copy, EditIni, Move, PlanError
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
    return {op.destination: op.source for op in operations if isinstance(op, Copy)}


def edited_ini(operations, text: str) -> str:
    for op in operations:
        if isinstance(op, EditIni):
            text = op.transform(text)
    return text


def test_v10_mirrors_its_archive_with_the_support_files_in_the_subfolder():
    operations = plan_patch(frozenset({"Game.exe"}), V10, library.FAMILIES["10"], Request("dxgi.dll"))

    assert copies(operations) == {
        "dxgi.dll": "OptiScaler.dll",
        "OptiScaler.ini": "OptiScaler.ini",
        "OptiScaler/D3D12_OptiScaler/D3D12Core.dll": "OptiScaler/D3D12_OptiScaler/D3D12Core.dll",
        "OptiScaler/amd_fidelityfx_upscaler_dx12.dll": "OptiScaler/amd_fidelityfx_upscaler_dx12.dll",
        "OptiScaler/libxess.dll": "OptiScaler/libxess.dll",
        "OptiScaler/dlssg_to_fsr3_amd_is_better.dll": "OptiScaler/dlssg_to_fsr3_amd_is_better.dll",
    }


def test_0_9_puts_everything_next_to_the_proxy_and_leaves_out_what_is_for_people():
    operations = plan_patch(frozenset({"Game.exe"}), V094, library.FAMILIES["0.9"], Request("winmm.dll"))
    placed = copies(operations)

    assert placed["winmm.dll"] == "OptiScaler.dll"
    assert {"libxess.dll", "fakenvapi.ini", "D3D12_Optiscaler/D3D12Core.dll"} <= placed.keys()
    assert not {"!!.txt", "setup_linux.sh", "setup_windows.bat", "Licenses/XeSS_LICENSE.txt", "OptiScaler.dll"} & placed.keys()


@pytest.mark.parametrize("path", ["Licenses/X.txt", "!!.txt", "setup_linux.sh", "OptiScaler/fetch.bat"])
def test_licenses_notes_and_setup_scripts_stay_in_the_archive(path):
    assert not is_for_the_game(path)


def test_the_games_files_are_backed_up_and_only_one_proxy_loads():
    entries = frozenset({"Game.exe", "libxess.dll", "version.dll", "dxgi.dll"})

    operations = plan_patch(entries, V094, library.FAMILIES["0.9"], Request("dxgi.dll"))

    assert Move("version.dll", "version.dll.b") in operations  # another proxy would load OptiScaler again
    assert Move("dxgi.dll", "dxgi.dll.b") in operations
    assert operations.index(Move("libxess.dll", "libxess.dll.b")) < operations.index(Copy("libxess.dll", "libxess.dll"))


def test_a_fresh_ini_gets_the_familys_defaults():
    operations = plan_patch(frozenset(), V10, library.FAMILIES["10"], Request("dxgi.dll"))
    archive_ini = "[FSR]\nFsr4GpuSupport=auto\nFsr4Model=auto\n\n[Menu]\nUseHQFont=auto\n"

    # FSR 4's model stays at auto: OptiScaler picks it for the GPU.
    assert edited_ini(operations, archive_ini) == "[FSR]\nFsr4GpuSupport=auto\nFsr4Model=auto\n\n[Menu]\nUseHQFont=false\n"


def test_a_kept_ini_is_left_as_the_user_set_it():
    users = "[FSR]\nFsr4GpuSupport=2\nFsr4Model=1\n\n[Menu]\nUseHQFont=true\n"

    operations = plan_patch(frozenset({"OptiScaler.ini"}), V10, library.FAMILIES["10"], Request("dxgi.dll"))

    assert Copy("OptiScaler.ini", "OptiScaler.ini") not in operations
    assert edited_ini(operations, users) == users


def test_asking_to_reset_the_ini_backs_up_the_games_and_places_the_versions():
    operations = plan_patch(frozenset({"OptiScaler.ini"}), V10, library.FAMILIES["10"], Request("dxgi.dll", True))

    assert operations.index(Move("OptiScaler.ini", "OptiScaler.ini.b")) < operations.index(
        Copy("OptiScaler.ini", "OptiScaler.ini")
    )


@pytest.mark.parametrize(
    ("files", "request_", "message"),
    [
        (V10, Request("d3d11.dll"), "Invalid proxy DLL name: d3d11.dll"),
        (V10 - {"OptiScaler.ini"}, Request("dxgi.dll"), "lacks OptiScaler.ini"),
    ],
)
def test_what_cannot_be_placed_is_refused(files, request_, message):
    with pytest.raises(PlanError, match=message):
        plan_patch(frozenset(), files, library.FAMILIES["10"], request_)
