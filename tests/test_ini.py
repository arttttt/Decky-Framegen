from framegen.domain import ini


def test_apply_bundle_defaults_replaces_only_auto_values():
    content = "FGInput=auto\nFGOutput = auto\nFsr4Update=auto\nLoadAsiPlugins=false\nUseHQFont=auto\nOther=auto\n"

    assert ini.apply_bundle_defaults(content) == (
        "FGInput=nukems\nFGOutput=nukems\nFsr4Update=true\nLoadAsiPlugins=false\nUseHQFont=false\nOther=auto\n"
    )


def test_migrate_fgtype_splits_into_input_and_output():
    assert ini.migrate_fgtype("[FrameGen]\nFGType=nukems\nX=1\n") == (
        "[FrameGen]\nFGInput=nukems\nFGOutput=nukems\nX=1\n"
    )


def test_migrate_fgtype_drops_stale_fgtype_when_fginput_exists():
    assert ini.migrate_fgtype("FGType=optifg\nFGInput=nukems\n") == "FGInput=nukems\n"


def test_migrate_fgtype_is_a_no_op_without_fgtype_and_idempotent():
    content = "[FrameGen]\nFGInput=auto\n"

    assert ini.migrate_fgtype(content) == content
    once = ini.migrate_fgtype("FGType=xefg\n")
    assert ini.migrate_fgtype(once) == once


def test_split_override_key():
    assert ini.split_override_key(" FSR . Fsr4ForceModel ") == ("FSR", "Fsr4ForceModel")
    assert ini.split_override_key("Fsr4ForceModel") == (None, "Fsr4ForceModel")
    assert ini.split_override_key(".Key") == (None, ".Key")
    assert ini.split_override_key("Section.") == (None, "Section.")


def test_apply_overrides_replaces_a_key_only_inside_its_section_keeping_crlf():
    content = "[A]\r\nKey=1\r\n[B]\r\nKey=1\r\n"

    assert ini.apply_overrides(content, {"B.Key": " 2 "}) == "[A]\r\nKey=1\r\n[B]\r\nKey=2\r\n"


def test_apply_overrides_inserts_a_missing_key_at_the_end_of_its_section():
    content = "[A]\nX=1\n\n[B]\nY=1\n"

    assert ini.apply_overrides(content, {"A.New": "v"}) == "[A]\nX=1\n\nNew=v\n[B]\nY=1\n"
    assert ini.apply_overrides("[A]\nX=1", {"A.New": "v"}) == "[A]\nX=1\nNew=v\n"


def test_apply_overrides_appends_a_missing_section():
    assert ini.apply_overrides("[A]\nX=1\n", {"Plugins.Load": "true"}) == "[A]\nX=1\n\n[Plugins]\nLoad=true\n"


def test_apply_overrides_bare_key_replaces_first_occurrence_or_appends():
    assert ini.apply_overrides("[A]\nK=1\n[B]\nK=1\n", {"K": "2"}) == "[A]\nK=2\n[B]\nK=1\n"
    assert ini.apply_overrides("[A]\nX=1\n", {"K": "2"}) == "[A]\nX=1\nK=2\n"


def test_apply_overrides_without_overrides_returns_content_unchanged():
    assert ini.apply_overrides("anything", {}) == "anything"
