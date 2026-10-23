"""Golden-file assertions for characterization tests.

A scenario records what it observes — directory trees, RPC results — as plain
data and compares it with `tests/golden/<name>.json`. Run with
`UPDATE_GOLDEN=1` to (re)write the files; review the diff like any code
change, since a changed golden file is a changed behaviour.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from conftest import KNOWN_CONTENT, REPO_ROOT, sha256

GOLDEN_DIR = Path(__file__).parent / "golden"

# Copies of the plugin's own files (its Python core, its launcher scripts) are
# named by their source path, so golden files do not change whenever that code does.
for _label, _root, _pattern in (("core", "py_modules", "*.py"), ("asset", "defaults/assets", "*")):
    for _source in (REPO_ROOT / _root).rglob(_pattern):
        if _source.is_file():
            KNOWN_CONTENT[sha256(_source.read_bytes())] = f"{_label}:{_source.relative_to(REPO_ROOT / _root).as_posix()}"

_CORE_SOURCES = frozenset(
    path.relative_to(REPO_ROOT / "py_modules").as_posix()
    for path in (REPO_ROOT / "py_modules" / "framegen").rglob("*.py")
)
COMPLETE_CORE = "core: a complete copy of py_modules/framegen"


def _collapse_core(tree: dict[str, object]) -> dict[str, object]:
    """Show a complete copy of the core as one line, so adding a module does not change every golden.

    An incomplete or altered copy keeps its per-file lines and shows up as a difference.
    """
    copies = {
        key: value[len("core:"):]
        for key, value in tree.items()
        if isinstance(value, str) and value.startswith("core:") and key.endswith(value[len("core:"):])
    }
    for prefix in {key[: len(key) - len(source)] for key, source in copies.items()}:
        package = f"{prefix}framegen"
        inside = {key for key in tree if key == package or key.startswith(package + "/")}
        files = {key for key in inside if tree[key] != "<dir>"}
        if {copies.get(key) for key in files} == set(_CORE_SOURCES):
            tree = {key: value for key, value in tree.items() if key not in inside}
            tree[package] = COMPLETE_CORE
    return tree


# Fields that differ between runs and say nothing about behaviour.
_VOLATILE_FIELDS = ("patched_at", "installed_at", "updated_at")


def _stabilize(value, root: Path):
    """Replace absolute paths under `root` and drop volatile fields, anywhere in a JSON value."""
    if isinstance(value, str):
        return value.replace(str(root), "<root>")
    if isinstance(value, list):
        return [_stabilize(item, root) for item in value]
    if isinstance(value, dict):
        return {key: _stabilize(item, root) for key, item in value.items() if key not in _VOLATILE_FIELDS}
    return value


def describe_tree(root: Path) -> dict[str, object]:
    """A readable, run-independent picture of a directory tree.

    Directories map to "<dir>". Files whose content is a known placeholder map
    to its label, text configs to their text, JSON (the patch marker,
    the install manifest) to its parsed form without volatile fields, and anything else to a short hash.
    """
    tree: dict[str, object] = {}
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_dir():
            tree[rel] = "<dir>"
            continue
        data = path.read_bytes()
        if path.name == "FRAMEGEN_PATCH" or path.suffix == ".json":
            tree[rel] = _stabilize(json.loads(data), root)
        elif sha256(data) in KNOWN_CONTENT:
            tree[rel] = KNOWN_CONTENT[sha256(data)]
        elif path.suffix in (".ini", ".txt"):
            tree[rel] = data.decode()
        else:
            tree[rel] = f"sha256:{sha256(data)[:16]}"
    return _collapse_core(tree)


def normalize_result(result: dict, root: Path) -> dict:
    """An RPC result with temp paths replaced, so it is stable across runs."""
    return _stabilize(result, root)


def assert_golden(name: str, observed: object) -> None:
    path = GOLDEN_DIR / f"{name}.json"
    rendered = json.dumps(observed, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if os.environ.get("UPDATE_GOLDEN") == "1":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered, encoding="utf-8")
        return
    assert path.exists(), f"missing golden file {path}; run with UPDATE_GOLDEN=1 to create it"
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert json.loads(rendered) == expected, f"behaviour differs from {path.name}"
