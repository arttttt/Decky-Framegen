"""The plugin's core and launch scripts in ~/deckyscaler (integration)."""

from conftest import REPO_ROOT, write
from deckyscaler.domain import bundle
from deckyscaler.infrastructure import core_install


def test_refreshing_replaces_the_core_and_scripts_and_leaves_the_rest(tmp_path):
    plugin_home = tmp_path / "deckyscaler"
    write(plugin_home / "deckyscaler" / "stale_module.py", b"old core")
    write(plugin_home / "patch", b"old script")
    write(plugin_home / "library" / "versions" / "x" / "entry.json", b"{}")

    core_install.refresh_core(plugin_home, REPO_ROOT / "defaults" / "assets")

    assert not (plugin_home / "deckyscaler" / "stale_module.py").exists()
    assert (plugin_home / "deckyscaler" / "__main__.py").read_bytes() == (core_install.CORE_SOURCE / "__main__.py").read_bytes()
    for installed, source in bundle.LAUNCHER_SCRIPTS.items():
        assert (plugin_home / installed).read_bytes() == (REPO_ROOT / "defaults" / "assets" / source).read_bytes()
        assert (plugin_home / installed).stat().st_mode & 0o111 == 0o111
    assert (plugin_home / "library" / "versions" / "x" / "entry.json").read_bytes() == b"{}"
    assert sorted(p.name for p in plugin_home.iterdir() if p.name.startswith(".")) == []
