import os

from framegen.infrastructure import files


def test_read_json_returns_empty_dict_for_missing_malformed_or_non_object(tmp_path):
    (tmp_path / "list.json").write_text("[1, 2]")
    (tmp_path / "broken.json").write_text("{not json")
    (tmp_path / "ok.json").write_text('{"a": 1}')

    assert files.read_json(tmp_path / "missing.json") == {}
    assert files.read_json(tmp_path / "list.json") == {}
    assert files.read_json(tmp_path / "broken.json") == {}
    assert files.read_json(tmp_path / "ok.json") == {"a": 1}


def test_rewrite_text_writes_only_when_the_content_changes(tmp_path):
    path = tmp_path / "OptiScaler.ini"
    path.write_text("A=1\n")
    os.utime(path, (1_000_000, 1_000_000))

    assert files.rewrite_text(path, lambda text: text) is False
    assert path.stat().st_mtime == 1_000_000

    assert files.rewrite_text(path, lambda text: text.replace("1", "2")) is True
    assert path.read_text() == "A=2\n"


def test_files_match_compares_content_and_requires_both_files(tmp_path):
    a = tmp_path / "a.dll"
    b = tmp_path / "b.dll"
    a.write_bytes(b"same")
    b.write_bytes(b"same")

    assert files.files_match(a, b) is True
    b.write_bytes(b"different")
    assert files.files_match(a, b) is False
    assert files.files_match(a, tmp_path / "missing.dll") is False
