from framegen.domain import ini


def test_set_values_replaces_a_key_only_inside_its_section_keeping_crlf():
    assert ini.set_values("[A]\r\nKey=1\r\n[B]\r\nKey=1\r\n", [("B", "Key", "2")]) == "[A]\r\nKey=1\r\n[B]\r\nKey=2\r\n"


def test_set_values_inserts_a_missing_key_or_section():
    assert ini.set_values("[A]\nX=1\n\n[B]\nY=1\n", [("A", "New", "v")]) == "[A]\nX=1\n\nNew=v\n[B]\nY=1\n"
    assert ini.set_values("[A]\nX=1\n", [("Plugins", "Load", "true")]) == "[A]\nX=1\n\n[Plugins]\nLoad=true\n"


def test_set_values_without_values_returns_content_unchanged():
    assert ini.set_values("anything", []) == "anything"


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
