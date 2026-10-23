"""The OptiScaler library's rules, against OptiScaler's real release listings (captured 2026-10-24)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from framegen.domain import library

FIXTURES = Path(__file__).parent / "fixtures"


def stable() -> list:
    return json.loads((FIXTURES / "optiscaler_stable.json").read_text())


def nightly() -> list:
    return json.loads((FIXTURES / "optiscaler_nightly.json").read_text())


# ── families ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("version", "family"),
    [("0.9.4", "0.9"), ("0.9.2a", "0.9"), ("10.0.0-pre1", "10"), ("10.3.1", "10"),
     ("0.7.9", None), ("0.10.0", None), ("11.0.0", None), ("garbage", None)],
)
def test_only_known_generations_have_a_family(version, family):
    found = library.family_of(version)

    assert (found.id if found else None) == family


def test_each_family_offers_its_own_fsr4_variants_as_ini_settings_with_a_default():
    assert library.FAMILIES["0.9"].default_variant == "sdk"
    assert library.FAMILIES["10"].default_variant == "auto"
    assert library.FAMILIES["10"].variants["int8"].ini == {"FSR.Fsr4GpuSupport": "2", "FSR.Fsr4Model": "1"}
    # 0.9 knows nothing of Fsr4Model, and 10 dropped the nukems FG setting.
    assert all("Fsr4Model" not in key for v in library.FAMILIES["0.9"].variants.values() for key in v.ini)
    assert "FrameGen.FGInput" not in library.FAMILIES["10"].ini_defaults


def test_an_archive_missing_a_required_file_is_reported():
    family = library.FAMILIES["10"]
    complete = frozenset({"OptiScaler.dll", "OptiScaler.ini", "OptiScaler/amd_fidelityfx_upscaler_dx12.dll", "x.txt"})

    assert library.missing_files(family, complete) == frozenset()
    assert library.missing_files(family, complete - {"OptiScaler.ini"}) == {"OptiScaler.ini"}


# ── stable channel ───────────────────────────────────────────────────────────


def test_stable_offers_every_0_9_release_newest_first_with_its_checksum():
    versions = library.available(library.STABLE, stable())
    supported = [v for v in versions if v.unsupported is None]

    assert [v.id for v in supported] == [
        "stable-0.9.4", "stable-0.9.3", "stable-0.9.2a", "stable-0.9.1", "stable-0.9.0"
    ]
    newest = supported[0]
    assert newest == library.Available(
        id="stable-0.9.4",
        channel="stable",
        version="0.9.4",
        date="20260718",
        published_at="2026-07-18T21:46:07Z",
        family="0.9",
        url="https://github.com/optiscaler/OptiScaler/releases/download/v0.9.4/Optiscaler_0.9.4-final.20260718._MM.7z",
        sha256="575cb4df866116093df75af607e37fd70e10f5163e0f23fd5c804142e80ef0ad",
        size=55016448,
        unsupported=None,
    )


def test_stable_lists_older_releases_as_unsupported_and_skips_its_old_prerelease():
    versions = library.available(library.STABLE, stable())
    older = [(v.id, v.unsupported) for v in versions if v.unsupported]

    # v0.7.9 and v0.7.8 name their archives differently; v0.7-old_nightly is a prerelease.
    assert older == [("stable-v0.7.9", library.NO_ARCHIVE), ("stable-v0.7.8", library.NO_ARCHIVE)]


# ── nightly channel ──────────────────────────────────────────────────────────


def test_nightly_offers_the_ten_newest_builds_named_by_date():
    versions = library.available(library.NIGHTLY, nightly())

    assert [v.id for v in versions] == [f"nightly-202610{day}" for day in range(23, 13, -1)]
    assert all(v.family == "10" and v.version == "10.0.0-pre1" and v.unsupported is None for v in versions)
    assert versions[0].url == (
        "https://github.com/optiscaler/OptiScaler-nightly/releases/download/"
        "nightly-20261023/OptiScaler_v10.0.0-pre1_20261023.7z"
    )


# ── what can't be read with certainty ────────────────────────────────────────


def newest_nightly(change) -> library.Available:
    listing = nightly()
    change(listing[0])
    return library.available(library.NIGHTLY, listing)[0]


@pytest.mark.parametrize(
    ("change", "reason"),
    [
        (lambda r: r["assets"].append(copy.deepcopy(r["assets"][0]) | {"name": "OptiScaler_v10.0.0-pre1_20261023.7z"}),
         library.SEVERAL_ARCHIVES),
        (lambda r: r.update(assets=[]), library.NO_ARCHIVE),
        (lambda r: r["assets"][0].update(name="OptiScaler_v10.0.0-pre1_20261023.zip"), library.NO_ARCHIVE),
        (lambda r: r["assets"][0].update(state="starter"), library.UPLOADING),
        (lambda r: r["assets"][0].pop("digest"), library.NO_CHECKSUM),
        (lambda r: r["assets"][0].update(digest="md5:abc"), library.NO_CHECKSUM),
        (lambda r: r["assets"][0].update(browser_download_url="https://example.com/OptiScaler.7z"), library.ELSEWHERE),
        (lambda r: r["assets"][0].update(name="OptiScaler_v11.0.0_20261023.7z",
                                         browser_download_url="https://github.com/optiscaler/OptiScaler-nightly/"
                                         "releases/download/nightly-20261023/OptiScaler_v11.0.0_20261023.7z"),
         library.UNKNOWN_FAMILY),
    ],
    ids=["several", "none", "not-7z", "uploading", "no-digest", "not-sha256", "elsewhere", "unknown-family"],
)
def test_a_version_that_cant_be_read_with_certainty_is_unsupported(change, reason):
    assert newest_nightly(change).unsupported == reason


def test_drafts_and_releases_of_the_other_kind_are_not_listed():
    listing = nightly()
    listing[0]["draft"] = True
    listing[1]["prerelease"] = False

    ids = [v.id for v in library.available(library.NIGHTLY, listing)]

    assert "nightly-20261023" not in ids and "nightly-20261022" not in ids


def test_a_listing_that_is_not_a_list_offers_nothing():
    assert library.available(library.STABLE, {"message": "API rate limit exceeded"}) == []


def test_versions_are_ordered_newest_first_whatever_order_github_sends():
    shuffled = list(reversed(stable()))

    ids = [v.id for v in library.available(library.STABLE, shuffled)]

    assert ids[:2] == ["stable-0.9.4", "stable-0.9.3"]


def test_a_version_released_twice_is_offered_once_from_the_newest_release():
    listing = stable()
    reupload = copy.deepcopy(listing[0])
    reupload["tag_name"] = "v0.9.4-fix"
    reupload["published_at"] = "2026-07-20T10:00:00Z"
    asset = reupload["assets"][0]
    asset["name"] = "Optiscaler_0.9.4-final.20260720._Reup.7z"
    asset["browser_download_url"] = f"https://github.com/optiscaler/OptiScaler/releases/download/v0.9.4-fix/{asset['name']}"
    listing.append(reupload)

    versions = [v for v in library.available(library.STABLE, listing) if v.id == "stable-0.9.4"]

    assert len(versions) == 1
    assert versions[0].date == "20260720"
