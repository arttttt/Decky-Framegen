"""The plugin's core and launch scripts in ~/fgmod (integration)."""

from conftest import REPO_ROOT, write
from framegen.domain import bundle
from framegen.infrastructure import fgmod_home


def test_refreshing_replaces_the_core_and_scripts_and_leaves_the_rest(tmp_path):
    fgmod = tmp_path / "fgmod"
    write(fgmod / "framegen" / "stale_module.py", b"old core")
    write(fgmod / "fgmod", b"old script")
    write(fgmod / "update-optiscaler-config.py", b"a script the core replaced")
    write(fgmod / "library" / "versions" / "x" / "entry.json", b"{}")

    fgmod_home.refresh_core(fgmod, REPO_ROOT / "defaults" / "assets")

    assert not (fgmod / "framegen" / "stale_module.py").exists()
    assert (fgmod / "framegen" / "__main__.py").read_bytes() == (fgmod_home.CORE_SOURCE / "__main__.py").read_bytes()
    for installed, source in bundle.LAUNCHER_SCRIPTS.items():
        assert (fgmod / installed).read_bytes() == (REPO_ROOT / "defaults" / "assets" / source).read_bytes()
        assert (fgmod / installed).stat().st_mode & 0o111 == 0o111
    assert (fgmod / "library" / "versions" / "x" / "entry.json").read_bytes() == b"{}"
    assert not (fgmod / "update-optiscaler-config.py").exists()
    assert sorted(p.name for p in fgmod.iterdir() if p.name.startswith(".")) == []
