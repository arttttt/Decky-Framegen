from framegen.domain import bundle


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


def test_a_complete_install_requires_every_variants_files_and_the_shared_ones():
    required = set(bundle.required_install_paths())

    assert {"OptiScaler.dll", "OptiScaler.ini", "fgmod", bundle.INSTALL_MANIFEST_FILENAME, "plugins/OptiPatcher.asi"} <= required
    assert set(bundle.SUPPORT_FILES) <= required
    for variant_id, variant in bundle.FSR4_VARIANTS.items():
        assert f"{variant['dir_name']}/{bundle.FSR4_UPSCALER_FILENAME}" in required
        assert {f"{variant['dir_name']}/{extra['name']}" for extra in variant.get("extra_files", [])} <= required
        if bundle.variant_injector(variant_id):
            assert f"{variant['dir_name']}/renames/dxgi.dll" in required
