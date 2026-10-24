"""FSR 4 under Proton: the rules (unit) and a game's state and launch options through the plugin (integration)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import STABLE, add_gpu, run
from deckyscaler.domain import fsr4, keyvalues, launch_options

# ── unit: rules ──────────────────────────────────────────────────────────────


def mapping(entries: dict[str, str]) -> keyvalues.KeyValues:
    return {"installconfigstore": {"software": {"valve": {"steam": {"compattoolmapping": {
        appid: {"name": name, "config": "", "priority": "250"} for appid, name in entries.items()
    }}}}}}


@pytest.mark.parametrize(
    ("entries", "tool"),
    [
        ({"730": "GE-Proton11-11", "0": "proton_experimental"}, "GE-Proton11-11"),  # the game's own choice wins
        ({"0": "proton-cachyos"}, "proton-cachyos"),  # else the one for every game
        ({"730": "", "0": "GE-Proton11-1"}, "GE-Proton11-1"),  # an empty name is no choice
        ({}, None),  # Steam's default, which no file names
    ],
)
def test_the_games_tool_is_its_own_choice_else_the_global_one(entries, tool):
    assert fsr4.compat_tool(mapping(entries), "730") == tool


def test_no_mapping_section_means_steams_default():
    assert fsr4.compat_tool({}, "730") is None


def test_a_tool_manifest_names_its_tools_and_where_they_are():
    manifest = keyvalues.parse('"compatibilitytools" { "compat_tools" { "GE-Proton11-11" { "install_path" "." } "x" { } } }')

    assert fsr4.custom_tools(manifest) == {"ge-proton11-11": ".", "x": "."}
    assert fsr4.custom_tools({}) == {}


@pytest.mark.parametrize(
    ("tracking", "version"),
    [
        (json.dumps({"fsr4_files": {"drive_c/windows/system32/amdxcffx64.dll": {"version": "4.1.1", "md5_hash": "x"}}}), "4.1.1"),
        (json.dumps({"dlss_files": {}}), None),
        ("not json", None),
        ("[]", None),
        ("", None),
    ],
)
def test_the_fetched_dlls_version_comes_from_upscaler_files(tracking, version):
    assert fsr4.tracked_version(tracking) == version


def test_only_amds_vendor_id_is_amd():
    assert fsr4.is_amd("0x1002\n")
    assert not fsr4.is_amd("0x10de\n")
    assert not fsr4.is_amd("")


@pytest.mark.parametrize(
    ("amd", "reads", "in_prefix", "expected"),
    [
        (False, True, True, None),  # off AMD FSR 4 isn't the question
        (True, False, True, fsr4.State(fsr4.IN_PREFIX, "tool", "4.1.1")),  # there already, whatever the Proton now
        (True, True, False, fsr4.State(fsr4.WILL_FETCH, "tool")),
        (True, False, False, fsr4.State(fsr4.UNSUPPORTED, "tool")),
    ],
)
def test_the_state_says_what_the_game_has_or_will_get(amd, reads, in_prefix, expected):
    assert fsr4.state(amd, "tool", reads, in_prefix, "4.1.1") == expected


def test_the_variable_is_asked_for_on_amd_with_a_proton_that_reads_it():
    assert fsr4.wants_upgrade_variable(True, True)
    assert not fsr4.wants_upgrade_variable(True, False)
    assert not fsr4.wants_upgrade_variable(False, True)


def test_the_launch_options_carry_the_variable_when_asked():
    assert launch_options.managed("dxgi.dll", True) == "WINEDLLOVERRIDES=dxgi=n,b PROTON_FSR4_UPGRADE=1 SteamDeck=0 %command%"
    assert launch_options.managed("OptiScaler.asi", True) == "PROTON_FSR4_UPGRADE=1 SteamDeck=0 %command%"
    assert launch_options.is_managed(launch_options.managed("dxgi.dll", True))


# ── integration: through the plugin ──────────────────────────────────────────


def test_a_game_on_a_proton_that_fetches_fsr4_gets_the_variable_and_says_so(plugin, plugin_home, steam_library, amd_gpu):
    steam_library.add_game("730", "Fsr Game")
    steam_library.add_tool("GE-Proton11-11", reads_fsr4_variable=True)
    steam_library.set_compat_tools({"730": "GE-Proton11-11"})

    status = run(plugin.get_game_status("730"))
    patched = run(plugin.patch_game("730", "dxgi.dll", "", STABLE))

    assert status["fsr4"] == {"state": "will-fetch", "tool": "GE-Proton11-11", "version": None}
    assert patched["launch_options"] == "WINEDLLOVERRIDES=dxgi=n,b PROTON_FSR4_UPGRADE=1 SteamDeck=0 %command%"


def test_once_fetched_the_status_names_the_version_in_the_prefix(plugin, plugin_home, steam_library, amd_gpu):
    steam_library.add_game("730", "Fsr Game")
    steam_library.add_tool("GE-Proton11-11", reads_fsr4_variable=True)
    steam_library.set_compat_tools({"0": "GE-Proton11-11"})
    steam_library.add_fsr4_to_prefix("730", "4.1.1")

    assert run(plugin.get_game_status("730"))["fsr4"] == {"state": "in-prefix", "tool": "GE-Proton11-11", "version": "4.1.1"}


@pytest.mark.parametrize("tool", ["proton_experimental", None, "GE-Proton9-20"])
def test_a_proton_that_cant_fetch_fsr4_gets_no_variable(plugin, plugin_home, steam_library, amd_gpu, tool):
    steam_library.add_game("730", "Older Game")
    steam_library.add_tool("GE-Proton9-20", reads_fsr4_variable=False)
    if tool:
        steam_library.set_compat_tools({"730": tool})

    status = run(plugin.get_game_status("730"))
    patched = run(plugin.patch_game("730", "dxgi.dll", "", STABLE))

    assert status["fsr4"] == {"state": "unsupported", "tool": tool, "version": None}
    assert "PROTON_FSR4_UPGRADE" not in patched["launch_options"]


def test_off_amd_fsr4_is_not_mentioned_and_not_asked_for(plugin, plugin_home, steam_library, tmp_path):
    add_gpu(tmp_path / "sys", "card0", "0x10de")
    steam_library.add_game("730", "Fsr Game")
    steam_library.add_tool("GE-Proton11-11", reads_fsr4_variable=True)
    steam_library.set_compat_tools({"730": "GE-Proton11-11"})

    assert run(plugin.get_game_status("730"))["fsr4"] is None
    assert "PROTON_FSR4_UPGRADE" not in run(plugin.patch_game("730", "dxgi.dll", "", STABLE))["launch_options"]


def test_the_boot_gpu_decides_on_a_machine_with_two(plugin, plugin_home, steam_library, tmp_path):
    add_gpu(tmp_path / "sys", "card0", "0x1002", boot_vga=False)
    add_gpu(tmp_path / "sys", "card1", "0x10de", boot_vga=True)
    write_connector = tmp_path / "sys" / "class" / "drm" / "card1-DP-1"
    write_connector.mkdir(parents=True)
    steam_library.add_game("730", "Fsr Game")

    assert run(plugin.get_game_status("730"))["fsr4"] is None


def test_a_tool_installed_for_every_user_is_found_too(plugin, plugin_home, steam_library, amd_gpu, tmp_path):
    steam_library.add_game("730", "Fsr Game")
    steam_library.add_tool("proton-cachyos", reads_fsr4_variable=True, tools_dir=tmp_path / "system-compatibilitytools.d")
    steam_library.set_compat_tools({"730": "proton-cachyos"})

    assert run(plugin.get_game_status("730"))["fsr4"]["state"] == "will-fetch"


def test_a_tool_updated_in_place_is_read_again(plugin, plugin_home, steam_library, amd_gpu):
    import os

    steam_library.add_game("730", "Fsr Game")
    tool = steam_library.add_tool("GE-Proton11-11", reads_fsr4_variable=False)
    steam_library.set_compat_tools({"730": "GE-Proton11-11"})
    assert run(plugin.get_game_status("730"))["fsr4"]["state"] == "unsupported"

    (tool / "proton").write_text('os.environ.get("PROTON_FSR4_UPGRADE")\n')
    os.utime(tool / "proton", ns=(1, 2_000_000_000_000_000_000))  # a later mtime than the cached read

    assert run(plugin.get_game_status("730"))["fsr4"]["state"] == "will-fetch"


def ge_game(steam_library) -> Path:
    root = steam_library.add_game("730", "Fsr Game")
    steam_library.add_tool("GE-Proton11-11", reads_fsr4_variable=True)
    steam_library.set_compat_tools({"730": "GE-Proton11-11"})
    return root


def test_the_patch_links_the_driver_dll_from_the_prefix_where_optiscaler_looks(plugin, plugin_home, steam_library, amd_gpu):
    import os

    from conftest import NIGHTLY, snapshot

    root = ge_game(steam_library)
    before = snapshot(root)
    prefix_dll = steam_library.steamapps / "compatdata" / "730" / "pfx" / "drive_c" / "windows" / "system32" / "amdxcffx64.dll"

    assert run(plugin.patch_game("730", "dxgi.dll", "", NIGHTLY))["status"] == "success"
    # Proton fetches the DLL on the first launch; until then the link leads nowhere, which harms nothing.
    assert os.readlink(root / "OptiScaler" / "amdxcffx64.dll") == str(prefix_dll)

    assert run(plugin.unpatch_game("730"))["status"] == "success"
    assert snapshot(root) == before


def test_the_users_own_driver_dll_is_left_alone(plugin, plugin_home, steam_library, amd_gpu):
    from conftest import NIGHTLY, write

    root = ge_game(steam_library)
    write(root / "OptiScaler" / "amdxcffx64.dll", b"the user's FSR 4 build")

    assert run(plugin.patch_game("730", "dxgi.dll", "", NIGHTLY))["status"] == "success"
    assert (root / "OptiScaler" / "amdxcffx64.dll").read_bytes() == b"the user's FSR 4 build"
    assert not (root / "OptiScaler" / "amdxcffx64.dll").is_symlink()
    run(plugin.unpatch_game("730"))

    assert (root / "OptiScaler" / "amdxcffx64.dll").read_bytes() == b"the user's FSR 4 build"


def test_a_repatch_replaces_its_own_driver_link(plugin, plugin_home, steam_library, amd_gpu):
    from conftest import NIGHTLY

    root = ge_game(steam_library)
    run(plugin.patch_game("730", "dxgi.dll", "", NIGHTLY))
    run(plugin.patch_game("730", "dxgi.dll", "WINEDLLOVERRIDES=dxgi=n,b PROTON_FSR4_UPGRADE=1 SteamDeck=0 %command%", NIGHTLY))

    assert (root / "OptiScaler" / "amdxcffx64.dll").is_symlink()
    assert not (root / "OptiScaler" / "amdxcffx64.dll.b").exists()
