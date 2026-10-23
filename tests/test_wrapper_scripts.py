"""Characterization tests for the launch-option wrappers in ~/fgmod.

`fgmod` (defaults/assets/fgmod.sh) patches the game on every launch and then
starts it; `fgmod-uninstaller.sh` unpatches and starts it. Both are bash for
SteamOS-like Linux (bash 5, GNU coreutils), so these tests run on Linux only —
CI runs them on every PR.

Each scenario runs the real scripts against the fake ~/fgmod with stubs for
zenity, logger and python on PATH. In launch mode the "game" is a recorder that
writes the environment and arguments the wrapper started it with. Results are
compared with golden files, like the Python patch scenarios.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import REPO_ROOT, game_file, make_game_dir, write
from golden import assert_golden, describe_tree, normalize_result

pytestmark = pytest.mark.skipif(sys.platform != "linux", reason="the wrappers target Linux (bash 5, GNU sed)")

RECORDER = """#!/usr/bin/env bash
{
  echo "WINEDLLOVERRIDES=${WINEDLLOVERRIDES-<unset>}"
  echo "SteamDeck=${SteamDeck-<unset>}"
  printf 'arg=%s\\n' "$@"
} > "$RECORD_FILE"
"""


@pytest.fixture
def tools(tmp_path) -> Path:
    """Stand-ins for zenity, logger and tee, and one python for both `python` and `python3`.

    The tee stand-in sends the scripts' log (meant for /tmp) into the test's own directory.
    """
    bin_dir = tmp_path / "tools"
    stubs = {
        "tee": f'#!/usr/bin/env bash\nexec "{shutil.which("tee")}" -a "{tmp_path / "wrapper.log"}"\n',
        "zenity": "#!/usr/bin/env bash\nexit 0\n",
        "logger": "#!/usr/bin/env bash\nexit 0\n",
        "python": f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n',
        "python3": f'#!/usr/bin/env bash\nexec "{sys.executable}" "$@"\n',
        "launch-recorder": RECORDER,
    }
    for name, body in stubs.items():
        write(bin_dir / name, body.encode()).chmod(0o755)
    return bin_dir


@pytest.fixture
def wrapper_fgmod(fgmod) -> Path:
    """The fake bundle with the real launcher scripts installed, as the installer does."""
    for installed, source in (
        ("fgmod", "fgmod.sh"),
        ("fgmod-uninstaller.sh", "fgmod-uninstaller.sh"),
        ("update-optiscaler-config.py", "update-optiscaler-config.py"),
    ):
        shutil.copy2(REPO_ROOT / "defaults" / "assets" / source, fgmod / installed)
        (fgmod / installed).chmod(0o755)
    return fgmod


class Wrapper:
    def __init__(self, home: Path, fgmod: Path, tools: Path, tmp_path: Path):
        self.home, self.fgmod, self.tools, self.tmp_path = home, fgmod, tools, tmp_path
        self.record_file = tmp_path / "launch-record.txt"

    def run(self, script: str, *args: str, env: dict[str, str] | None = None) -> dict:
        """Run a wrapper script; returns its exit code and, in launch mode, what the game received."""
        self.record_file.unlink(missing_ok=True)
        result = subprocess.run(
            ["bash", str(self.fgmod / script), *args],
            env={
                "HOME": str(self.home),
                "PATH": f"{self.tools}:/usr/local/bin:/usr/bin:/bin",
                "RECORD_FILE": str(self.record_file),
                **(env or {}),
            },
            capture_output=True,
            text=True,
            timeout=60,
        )
        observed: dict = {"exit_code": result.returncode}
        if self.record_file.exists():
            observed["game_launched_with"] = self.record_file.read_text().splitlines()
        return normalize_result(observed, self.tmp_path)

    def launch(self, script: str, game_exe: Path, env: dict[str, str] | None = None) -> dict:
        """Steam launch mode: `<wrapper> %command%`, with the recorder standing in for the game."""
        return self.run(script, str(self.tools / "launch-recorder"), str(game_exe), "-dx12", env=env)


@pytest.fixture
def wrapper(home, wrapper_fgmod, tools, tmp_path) -> Wrapper:
    return Wrapper(home, wrapper_fgmod, tools, tmp_path)


def scenario(name: str, game: Path, steps: list[tuple[str, dict]]) -> None:
    assert_golden(name, [{"step": step, **observed} for step, observed in steps] + [{"final_tree": describe_tree(game)}])


# ── fgmod (patch on launch) ──────────────────────────────────────────────────


def test_patch_standalone_then_uninstall(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Clean Game")
    patched = wrapper.run("fgmod", str(game / "Game.exe"))
    after_patch = describe_tree(game)
    unpatched = wrapper.run("fgmod-uninstaller.sh", str(game / "Game.exe"))

    scenario(
        "wrapper_standalone_patch_then_uninstall",
        game,
        [("patch", {**patched, "tree": after_patch}), ("uninstall", unpatched)],
    )


def test_launch_mode_patches_then_starts_the_game_with_overrides(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Launch Game")

    launched = wrapper.launch("fgmod", game / "Game.exe", env={"DLL": "winmm.dll", "WINEDLLOVERRIDES": "d3d11=n"})

    scenario("wrapper_launch_mode", game, [("launch", launched)])


def test_game_shipped_files_across_patch_and_uninstall(wrapper, tmp_path):
    shipped = {
        name: game_file(name)
        for name in ("version.dll", "libxess.dll", "amd_fidelityfx_dx12.dll", "amdxcffx64.dll", "d3dcompiler_47.dll")
    }
    game = make_game_dir(tmp_path / "games" / "Shipping Game", {**shipped, "plugins/OtherMod.asi": game_file("OtherMod.asi")})

    patched = wrapper.run("fgmod", str(game / "Game.exe"), env={"DLL": "version.dll"})
    after_patch = describe_tree(game)
    unpatched = wrapper.run("fgmod-uninstaller.sh", str(game / "Game.exe"))

    scenario(
        "wrapper_game_shipped_files",
        game,
        [("patch", {**patched, "tree": after_patch}), ("uninstall", unpatched)],
    )


def test_variant_from_env_and_repatch_on_every_launch(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Variant Game")

    first = wrapper.run("fgmod", str(game / "Game.exe"), env={"FGMOD_FSR4_VARIANT": "rdna2-valve-411-pre10"})
    after_valve = describe_tree(game)
    second = wrapper.run("fgmod", str(game / "Game.exe"))  # manifest default: rdna23-int8

    scenario(
        "wrapper_variant_and_repatch",
        game,
        [("patch valve", {**first, "tree": after_valve}), ("patch default", second)],
    )


def test_existing_ini_is_migrated_and_env_overrides_applied(wrapper, tmp_path):
    ini = b"[Upscalers]\nDx12Upscaler=auto\n\n[FrameGen]\nFGType=nukems\n\n[Menu]\nUseHQFont=auto\n"
    game = make_game_dir(tmp_path / "games" / "Ini Game", {"OptiScaler.ini": ini})

    patched = wrapper.run("fgmod", str(game / "Game.exe"), env={"Dx12Upscaler": "fsr31", "OptiScaler_Menu_UseHQFont": "true"})

    scenario("wrapper_existing_ini", game, [("patch", patched)])


def test_unreal_engine_layout_patches_the_binaries_directory(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Unreal Game")
    write(game / "Engine" / "Binaries" / "ThirdParty" / "x.dll", game_file("x.dll"))
    write(game / "UnrealGame" / "Binaries" / "Win64" / "UnrealGame-Win64-Shipping.exe", game_file("shipping.exe"))

    patched = wrapper.run("fgmod", str(game / "Game.exe"))

    scenario("wrapper_unreal_layout", game, [("patch", patched)])


def test_a_launcher_command_patches_the_game_binarys_directory(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Cyberpunk 2077")
    write(game / "REDprelauncher.exe", game_file("REDprelauncher.exe"))
    write(game / "bin" / "x64" / "Cyberpunk2077.exe", game_file("Cyberpunk2077.exe"))

    launched = wrapper.launch("fgmod", game / "REDprelauncher.exe")

    scenario("wrapper_launcher_remap", game, [("launch", launched)])


def test_a_directory_argument_and_a_reset_ini(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Dir Game", {"OptiScaler.ini": b"[Menu]\nUseHQFont=auto\nMine=1\n"})

    kept = wrapper.run("fgmod", str(game))
    kept_ini = (game / "OptiScaler.ini").read_text()
    reset = wrapper.run("fgmod", str(game), env={"PRESERVE_INI": "false"})

    scenario("wrapper_directory_argument_and_reset_ini", game, [("patch", {**kept, "ini": kept_ini}), ("reset ini", reset)])


def test_steams_install_path_is_the_fallback_and_separators_are_dropped(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Fallback Game")

    launched = wrapper.run(
        "fgmod", "--", str(wrapper.tools / "launch-recorder"), "run", env={"STEAM_COMPAT_INSTALL_PATH": str(game)}
    )

    scenario("wrapper_steam_install_path_fallback", game, [("launch", launched)])


def test_a_game_proxy_identical_to_ours_and_other_variants(wrapper, fgmod, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Proxy Game", {"dxgi.dll": (fgmod / "renames" / "dxgi.dll").read_bytes()})

    native = wrapper.run("fgmod", str(game / "Game.exe"), env={"FGMOD_FSR4_VARIANT": "rdna4-native"})
    after_native = describe_tree(game)
    override = wrapper.run("fgmod", str(game / "Game.exe"), env={"FGMOD_FSR4_VARIANT": "rdna34-official-411"})

    scenario(
        "wrapper_identical_proxy_and_variants",
        game,
        [("patch rdna4-native", {**native, "tree": after_native}), ("patch rdna34-official-411", override)],
    )


def test_usage_errors(wrapper):
    assert wrapper.run("fgmod")["exit_code"] == 1
    assert wrapper.run("fgmod-uninstaller.sh")["exit_code"] == 1


def test_missing_game_directory_is_an_error(wrapper, tmp_path):
    result = wrapper.run("fgmod", str(tmp_path / "nowhere" / "Game.exe"))

    assert result["exit_code"] == 1


# ── fgmod-uninstaller.sh ─────────────────────────────────────────────────────


def test_uninstaller_follows_unreal_layouts(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Unreal Uninstall")
    write(game / "Engine" / "Binaries" / "ThirdParty" / "x.dll", game_file("x.dll"))
    write(game / "UnrealGame" / "Binaries" / "Win64" / "UnrealGame-Win64-Shipping.exe", game_file("shipping.exe"))
    wrapper.run("fgmod", str(game / "Game.exe"))

    unpatched = wrapper.run("fgmod-uninstaller.sh", str(game / "Game.exe"))

    scenario("wrapper_uninstaller_unreal_layout", game, [("uninstall", unpatched)])


def test_uninstaller_refuses_to_run_on_the_bundle_itself(wrapper):
    result = wrapper.run("fgmod-uninstaller.sh", str(wrapper.fgmod / "Game.exe"))

    assert result["exit_code"] == 1
    assert (wrapper.fgmod / "OptiScaler.dll").exists()


def test_uninstaller_launch_mode_starts_the_game(wrapper, tmp_path):
    game = make_game_dir(tmp_path / "games" / "Uninstall Game")
    wrapper.run("fgmod", str(game / "Game.exe"), env={"DLL": "version.dll"})

    launched = wrapper.launch("fgmod-uninstaller.sh", game / "Game.exe")

    scenario("wrapper_uninstaller_launch_mode", game, [("launch", launched)])
