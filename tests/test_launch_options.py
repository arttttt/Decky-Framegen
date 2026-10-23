import pytest

from framegen.domain import launch_options


@pytest.mark.parametrize(
    ("dll_name", "expected"),
    [
        ("dxgi.dll", "WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%"),
        ("winhttp.dll", "WINEDLLOVERRIDES=winhttp=n,b SteamDeck=0 %command%"),
        ("OptiScaler.asi", "SteamDeck=0 %command%"),
    ],
)
def test_managed_options_per_proxy(dll_name, expected):
    assert launch_options.managed(dll_name) == expected


@pytest.mark.parametrize("dll_name", ["dxgi.dll", "winmm.dll", "version.dll", "dbghelp.dll", "winhttp.dll", "wininet.dll"])
def test_options_written_for_a_dll_proxy_are_recognised_as_managed(dll_name):
    assert launch_options.is_managed(launch_options.managed(dll_name))


def test_is_managed_tolerates_extra_whitespace_and_recognises_the_wrapper():
    assert launch_options.is_managed("  WINEDLLOVERRIDES=dxgi=n,b    SteamDeck=0 %command%  ")
    assert launch_options.is_managed("~/fgmod/fgmod %command%")


@pytest.mark.parametrize("options", ["", "   ", "mangohud %command%", "WINEDLLOVERRIDES=d3d11=n,b %command%"])
def test_user_options_are_not_managed(options):
    assert not launch_options.is_managed(options)


def test_asi_options_are_not_recognised_as_managed():
    # Current behaviour: the ASI proxy writes no override, so its options look like the user's own.
    assert not launch_options.is_managed(launch_options.managed("OptiScaler.asi"))


@pytest.mark.parametrize(
    ("current", "dll_name", "expected"),
    [
        ("", "dxgi.dll", "dxgi=n,b"),
        ("d3d11=n", "winmm.dll", "d3d11=n;winmm=n,b"),
        ("d3d11,dxgi=n;xinput1_3=b", "version.dll", "d3d11,dxgi=n;xinput1_3=b;version=n,b"),
        ("d3d11=n", "OptiScaler.asi", "d3d11=n"),
    ],
)
def test_wine_dll_overrides_append_our_entry_with_wines_separator(current, dll_name, expected):
    assert launch_options.wine_dll_overrides(current, dll_name) == expected
