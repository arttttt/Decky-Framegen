"""Valve's KeyValues text format (unit)."""

from deckyscaler.domain import keyvalues

CONFIG = r'''"InstallConfigStore"
{
	"Software"
	{
		"Valve"
		{
			"Steam"
			{
				// per-game tools
				"CompatToolMapping"
				{
					"1091500"
					{
						"name"		"GE-Proton11-11"
						"config"		""
					}
				}
				"Path"		"C:\\Games \"quoted\""
			}
		}
	}
}
'''


def test_nested_sections_are_read_and_found_case_insensitively():
    tree = keyvalues.parse(CONFIG)

    assert keyvalues.find(tree, "InstallConfigStore", "Software", "Valve", "Steam", "CompatToolMapping", "1091500", "name") == "GE-Proton11-11"
    assert keyvalues.find(tree, "installconfigstore", "software", "valve", "steam", "path") == 'C:\\Games "quoted"'


def test_a_missing_step_finds_nothing():
    tree = keyvalues.parse(CONFIG)

    assert keyvalues.find(tree, "InstallConfigStore", "Nope", "Valve") is None
    assert keyvalues.find(tree, "InstallConfigStore", "Software", "Valve", "Steam", "Path", "deeper") is None


def test_bare_tokens_comments_and_a_repeated_key():
    tree = keyvalues.parse('root { install_path . // the tool\n key "a" key "b" }')

    assert tree == {"root": {"install_path": ".", "key": "b"}}


def test_malformed_input_keeps_what_was_read():
    assert keyvalues.parse('"a" { "b" "c" ') == {"a": {"b": "c"}}
    assert keyvalues.parse("} } \"x\" \"y\"") == {"x": "y"}
    assert keyvalues.parse("") == {}
