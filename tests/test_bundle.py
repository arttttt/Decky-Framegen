from framegen import bundle


def test_select_variant_prefers_a_valid_requested_variant():
    assert bundle.select_variant("rdna4-native", "rdna2-valve-411-pre10") == "rdna4-native"


def test_select_variant_falls_back_to_the_bundle_default():
    assert bundle.select_variant("not-a-variant", "rdna2-valve-411-pre10") == "rdna2-valve-411-pre10"
    assert bundle.select_variant(None, " rdna34-official-411 ") == "rdna34-official-411"


def test_select_variant_falls_back_to_the_global_default():
    assert bundle.select_variant("", "also-unknown") == bundle.DEFAULT_FSR4_VARIANT
    assert bundle.select_variant(None, None) == bundle.DEFAULT_FSR4_VARIANT


def test_normalize_variant_maps_unknown_ids_to_the_default():
    assert bundle.normalize_variant(" rdna4-native ") == "rdna4-native"
    assert bundle.normalize_variant("rdna5") == bundle.DEFAULT_FSR4_VARIANT
    assert bundle.normalize_variant(None) == bundle.DEFAULT_FSR4_VARIANT
