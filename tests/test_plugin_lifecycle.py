"""What Decky Loader does to the plugin on its own, outside any RPC."""

import main


def test_the_plugin_has_no_uninstall_hook():
    # Decky runs a plugin's `_uninstall` on every update, not only on removal
    # (decky-loader v3.3.0: browser.py `stop(uninstall=True)` -> sandboxed_plugin.py `_uninstall`).
    # A cleanup hook there would wipe ~/deckyscaler each time a new build is installed.
    assert not hasattr(main.Plugin, "_uninstall")
