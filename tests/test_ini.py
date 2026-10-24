from framegen.domain import ini


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


SAMPLE = "[Upscalers]\nDx12Upscaler=auto\n\n[FrameGen]\nEnabled=auto\nFGInput=auto\n\n[V-Sync]\nEnabled=auto\n"


def test_env_variables_name_a_key_three_ways():
    environ = {
        "OptiScaler_Upscalers_Dx12Upscaler": "xess",  # full
        "FrameGen_Enabled": "true",  # section and key
        "FGInput": "fsrfg",  # a key found in one section only
    }

    assert ini.env_overrides(SAMPLE, environ) == [
        ("Upscalers", "Dx12Upscaler", "xess"), ("FrameGen", "Enabled", "true"), ("FrameGen", "FGInput", "fsrfg"),
    ]


def test_a_section_can_be_spelled_without_dashes_and_dots():
    assert ini.env_overrides(SAMPLE, {"VSync_Enabled": "x", "OptiScaler_VSync_Enabled": "y"}) == [
        ("V-Sync", "Enabled", "x"), ("V-Sync", "Enabled", "y"),
    ]


def test_variables_that_name_no_single_existing_key_are_left_out():
    environ = {"Enabled": "true", "PATH": "/usr/bin", "FrameGen_Missing": "1", "Nope_Dx12Upscaler": "1", "OptiScaler_Bad": "1"}

    assert ini.env_overrides(SAMPLE, environ) == []


def test_env_values_are_written_verbatim():
    values = ini.env_overrides(SAMPLE, {"Dx12Upscaler": r"C:\Games\x \1 & more"})

    assert ini.set_values(SAMPLE.replace("\n", "\r\n"), values).startswith("[Upscalers]\r\nDx12Upscaler=C:\\Games\\x \\1 & more\r\n")
