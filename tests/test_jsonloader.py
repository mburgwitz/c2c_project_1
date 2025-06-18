import json
import pytest
from pathlib import Path
from src.util.config.loaders import (
    JSONLoader,
    FileNotSpecified,
    FileNotFound,
    FileFormatError,
    FilePermissionError,
    FileIOError,
)

@pytest.fixture
def loader(tmp_path):
    # No default filenames used
    return JSONLoader(base_path=tmp_path)

def test_load_single_valid(tmp_path, loader):
    # Generate a valid JSON file, first as a dict
    data = {"foo": 1, "bar": [1,2,3]}
    fp = tmp_path / "a.json"

    # write JSON data with write_text to temporary file a.json
    # json.dumps converts dict data to correct json
    fp.write_text(json.dumps(data), encoding="utf-8")

    result = loader.load("a.json")
    assert result == data

def test_load_multiple_valid(tmp_path, loader):
    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    result = loader.load(["a.json", "b.json"])
    assert isinstance(result, dict)
    assert result["a.json"] == a
    assert result["b.json"] == b

def test_file_not_specified(loader):
    with pytest.raises(FileNotSpecified):
        loader.load(None)

def test_file_not_found(tmp_path, loader):
    with pytest.raises(FileNotFound) as ei:
        loader.load("nope.json")
    # prüfen, dass das path-Attribut stimmt
    assert ei.value.path == tmp_path / "nope.json"

def test_format_error(tmp_path, loader):
    # Schreibe ungültiges JSON
    fp = tmp_path / "bad.json"
    fp.write_text("{ not: valid, }", encoding="utf-8")

    with pytest.raises(FileFormatError) as ei:
        loader.load("bad.json")
    assert ei.value.path == fp
    # original_exception ist JSONDecodeError
    assert isinstance(ei.value.original_exception, json.JSONDecodeError)

def test_permission_error(tmp_path, loader, monkeypatch):
    # Simuliere PermissionError beim read_text
    fp = tmp_path / "p.json"
    fp.write_text("{}", encoding="utf-8")

    def fake_read_text(*args, **kwargs):
        raise PermissionError("denied")
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    with pytest.raises(FilePermissionError) as ei:
        loader.load("p.json")
    assert ei.value.path == fp
    assert isinstance(ei.value.original_exception, PermissionError)

def test_io_error(tmp_path, loader, monkeypatch):
    # Simuliere OSError
    fp = tmp_path / "i.json"
    fp.write_text("{}", encoding="utf-8")

    def fake_read_text(*args, **kwargs):
        raise OSError("disk full")
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    with pytest.raises(FileIOError) as ei:
        loader.load("i.json")
    assert ei.value.path == fp
    assert isinstance(ei.value.original_exception, OSError)

def test_catchall_wraps_unexpected(tmp_path, loader, monkeypatch):
    # Simuliere einen beliebigen Fehler im json.loads
    fp = tmp_path / "u.json"
    fp.write_text("{}", encoding="utf-8")

    def fake_json_loads(_):
        raise RuntimeError("wtf")
    monkeypatch.setattr("json.loads", fake_json_loads)

    with pytest.raises(Exception) as ei:
        loader.load("u.json")
    # je nach Implementation kann das LoaderError oder OSError sein
    assert "loading" in str(ei.value)