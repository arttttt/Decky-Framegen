"""Resetting a game an earlier plugin version patched: rules (unit)."""

from __future__ import annotations

import pytest

from framegen.domain import stock_reset
from framegen.domain.patch_plan import DeleteFile, Move, RemoveTree

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
    assert set(reset.unrecoverable) == {"amd_fidelityfx_dx12.dll", "nvapi64.dll"}
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
