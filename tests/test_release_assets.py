import pytest

from deckyscaler.domain import release_assets

HEX = "575cb4df866116093df75af607e37fd70e10f5163e0f23fd5c804142e80ef0ad"


def test_the_sha256_comes_from_githubs_digest():
    assert release_assets.sha256({"digest": f"sha256:{HEX}"}) == HEX


@pytest.mark.parametrize("asset", [{}, {"digest": None}, {"digest": f"md5:{HEX}"}, {"digest": f"sha256:{HEX[:-1]}"},
                                   {"digest": f"sha256:{HEX.upper()}"}])
def test_anything_else_is_no_usable_checksum(asset):
    assert release_assets.sha256(asset) is None
