"""Reading the settings an OptiScaler.ini offers from its own comments (unit), against snippets and the
real files the nightly and 0.9.4 ship (tests/fixtures/optiscaler-ini)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from deckyscaler.domain import ini_schema
from deckyscaler.domain.ini_schema import BOOL, ENUM, NUMBER, TEXT, Choice

FIXTURES = Path(__file__).parent / "fixtures" / "optiscaler-ini"


def one(block: str, key: str = "Key", section: str = "S"):
    """The setting a single commented key in a section reads as."""
    sections = ini_schema.parse(f"[{section}]\n{block}\n{key}=auto\n")
    return sections[0].settings[0]


def nightly() -> dict:
    sections = ini_schema.parse((FIXTURES / "nightly-20261024.ini").read_bytes().decode("utf-8"))
    return {(s.section, s.key): s for section in sections for s in section.settings}


# ── shapes ───────────────────────────────────────────────────────────────────


def test_true_or_false_is_a_toggle_with_its_default():
    setting = one("; Enables Frame Generation\n; true or false - Default (auto) is false")

    assert (setting.kind, setting.default, setting.description) == (BOOL, "false", "Enables Frame Generation")


@pytest.mark.parametrize(
    ("line", "choices"),
    [
        ("; 0 = Trace / 1 = Debug / 2 = Info", [("0", "Trace"), ("1", "Debug"), ("2", "Info")]),
        ("; 0: Input | 1: Present | 2: Zero", [("0", "Input"), ("1", "Present"), ("2", "Zero")]),
        ("; 2 - AntiLag 2, 3 - Reflex, 4 - XeLL", [("2", "AntiLag 2"), ("3", "Reflex"), ("4", "XeLL")]),
        ("; 1 = 2X | 2 = 3X | 3 Bottom Right", [("1", "2X"), ("2", "3X"), ("3", "Bottom Right")]),
    ],
)
def test_a_numbered_list_is_a_choice_whatever_its_separators(line, choices):
    setting = one(f"; Something\n{line}\n; Default (auto) is 1")

    assert setting.kind == ENUM
    assert [(c.value, c.label) for c in setting.choices] == choices


def test_one_pair_per_line_is_a_choice_too():
    setting = one("; Mode\n; 0 = Off\n; 1 = On\n; 2 = Auto\n; Default (auto) is 2")

    assert setting.choices == (Choice("0", "Off"), Choice("1", "On"), Choice("2", "Auto"))
    assert setting.default == "2"


def test_a_numbered_list_beats_a_copied_true_or_false_line():
    setting = one("; Frame count\n; 1 = 2X | 2 = 3X\n; true or false - Default (auto) is 1")

    assert (setting.kind, setting.default) == (ENUM, "1")


@pytest.mark.parametrize(
    ("line", "values", "default"),
    [
        ("; nofg, fsrfg, xefg - Default (auto) is nofg", ["nofg", "fsrfg", "xefg"], "nofg"),
        ("; rcas, da or lcda - Default (auto) is rcas", ["rcas", "da", "lcda"], "rcas"),
        ("; fsr22 (native DX11), xess (native DX11, Arc only), dlss - Default (auto) is fsr22", ["fsr22", "xess", "dlss"], "fsr22"),
        ("; None, Nukems, FFX - Default (auto) is Nukems", ["None", "Nukems", "FFX"], "Nukems"),
    ],
)
def test_a_word_list_is_a_choice_of_those_words(line, values, default):
    setting = one(f"; Pick one\n{line}")

    assert setting.kind == ENUM
    assert [c.value for c in setting.choices] == values
    assert setting.default == default


def test_a_word_list_may_put_its_default_on_the_next_line():
    setting = one("; Dx12\n; xess, fsr22, dlss\n; Default (auto) is DLSS when capable gpu, XeSS otherwise")

    assert [c.value for c in setting.choices] == ["xess", "fsr22", "dlss"]
    assert setting.default is None  # stated in prose: OptiScaler decides


@pytest.mark.parametrize(
    ("line", "minimum", "maximum", "integer"),
    [
        ("; 0.0 - 2.0  - Default (auto) is 0.3", 0.0, 2.0, False),
        ("; -1000 - 1000 - Default (auto) is 0", -1000.0, 1000.0, True),
        ("; From 0 to 4 - Default (auto) is 0", 0.0, 4.0, True),
        ("; -1.0 to 1.0 - Default (auto) is 0.0", -1.0, 1.0, False),
        ("; value range between 0.0 and 1.0 (while using upper limit is RCAS 1.3) - Default (auto) is 0.3", 0.0, 1.0, False),
        ("; 300.0 or more - Default (auto) is 700.0", 300.0, None, False),
        ("; 0.0 to max float value - Default (auto) is 0.1", 0.0, None, False),
    ],
)
def test_a_range_is_a_number_within_it(line, minimum, maximum, integer):
    setting = one(f"; A number\n{line}")

    assert (setting.kind, setting.minimum, setting.maximum, setting.integer) == (NUMBER, minimum, maximum, integer)


def test_numbers_in_prose_are_not_a_range():
    setting = one("; Extends Scaling Ratio limits to 0.1 - 6.0\n; true or false - Default (auto) is false")

    assert setting.kind == BOOL


def test_a_list_of_whole_numbers_is_a_choice_or_an_open_number():
    closed = one("; Anisotropy\n; 2, 4, 8, 16 - Default (auto) is disabled")
    open_ended = one("; Rounding\n; 2, 4, 8, 16 ...  - Default (auto) is disabled")

    assert [c.value for c in closed.choices] == ["2", "4", "8", "16"] and closed.default is None
    assert (open_ended.kind, open_ended.minimum, open_ended.integer) == (NUMBER, 2.0, True)


def test_a_type_word_types_the_value_and_a_hex_default_stays_hex():
    setting = one("; Menu key\n; Integer value - Default (auto) is 0x2D which equals VK_INSERT\n; -1 -> No shortcut key")

    assert (setting.kind, setting.integer, setting.default) == (NUMBER, True, "0x2D")


def test_a_key_its_comments_dont_type_is_free_text():
    setting = one("; Path of the nvngx.dll\n; nvngx.dll or _nvngx.dll")

    assert (setting.kind, setting.default) == (TEXT, None)
    assert setting.help == "Path of the nvngx.dll\nnvngx.dll or _nvngx.dll"


def test_keys_right_after_a_commented_key_share_its_comments():
    sections = ini_schema.parse("[Magnifier]\n; Offset\n; -1000 - 1000 - Default (auto) is 0\nX=auto\nY=auto\n\nZ=auto\n")

    x, y, z = sections[0].settings
    assert (x.kind, y.kind, y.minimum) == (NUMBER, NUMBER, -1000.0)
    assert (z.kind, z.help) == (TEXT, "")  # an empty line ends the block


def test_section_dashes_are_not_part_of_a_description():
    sections = ini_schema.parse("; ----\n[A]\n; ----\n; Enables it\n; true or false - Default (auto) is true\nOn=auto\n")

    assert sections[0].settings[0].description == "Enables it"


# ── the real files ───────────────────────────────────────────────────────────


def test_every_key_of_the_nightly_ini_is_offered_and_most_are_typed():
    settings = nightly()
    kinds = Counter(s.kind for s in settings.values())

    assert len(settings) == 327
    assert kinds[BOOL] == 176
    assert kinds[ENUM] + kinds[NUMBER] >= 100
    assert kinds[TEXT] <= 50  # paths, names, prose-only keys


def test_keys_are_told_apart_by_section():
    settings = nightly()

    assert settings[("XeFG", "InterpolationCount")].choices != settings[("DLSSG", "InterpolationCount")].choices
    assert ("FrameGen", "Enabled") in settings and ("Sharpness", "OverrideSharpness") in settings


@pytest.mark.parametrize(
    ("section", "key", "kind", "default", "values"),
    [
        ("FrameGen", "FTInput", ENUM, "0", ["0", "1", "2"]),
        ("fakenvapi", "LowLatencyInput", ENUM, None, ["2", "3", "4", "5"]),
        ("Log", "LogLevel", ENUM, "0", ["0", "1", "2", "3", "4"]),
        ("Upscalers", "Dx11Upscaler", ENUM, "fsr22", ["fsr22", "fsr31", "xess", "xess_12", "fsr21_12", "fsr22_12", "ffx_12", "dlss"]),
        ("FSR", "Fsr4GpuSupport", ENUM, "0", ["0", "1", "2", "3", "4"]),
        ("FrameGen", "FGInput", ENUM, "nofg", ["nofg", "dlssg", "nvngxfg", "fsrfg", "upscaler", "fsrfg30", "xefg"]),
        ("Libraries", "NvngxPath", TEXT, None, []),
    ],
)
def test_known_nightly_keys_read_as_their_comments_say(section, key, kind, default, values):
    setting = nightly()[(section, key)]

    assert (setting.kind, setting.default, [c.value for c in setting.choices]) == (kind, default, values)


def test_the_0_9_4_ini_reads_with_the_same_rules():
    sections = ini_schema.parse((FIXTURES / "0.9.4.ini").read_bytes().decode("utf-8"))
    settings = {(s.section, s.key): s for section in sections for s in section.settings}

    assert len(settings) == 288
    assert "nukems" in [c.value for c in settings[("FrameGen", "FGInput")].choices]
    assert settings[("FSR", "Fsr4Update")].kind == BOOL


def test_an_empty_line_parts_a_comment_from_the_key_below_it():
    sections = ini_schema.parse("[A]\n; About something else\n\nKey=auto\n")

    assert sections[0].settings[0].help == ""


def test_a_toggle_whose_default_isnt_true_or_false_has_none():
    assert one("; Toggle\n; true or false - Default (auto) is 1").default is None
