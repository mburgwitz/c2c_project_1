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
    LoaderError
)

@pytest.fixture
def loader(tmp_path):
    # No default filenames used
    return JSONLoader(base_path=tmp_path)

# check if attributes like errors, messages and path is received and returned correctly
# uses buildin fixutre tmp_path 

#-------------------------------------------
# Test defined expections for jsonloader
#-------------------------------------------

@pytest.mark.exception
def test_filenotspecified_str():
    e = FileNotSpecified()
    # check instance
    assert isinstance(e, LoaderError)
    # check error message
    assert str(e) == "No filename specified"

@pytest.mark.exception
def test_filenotfound_attributes_and_msg(tmp_path):
    p = tmp_path / "missing.json"
    exc = FileNotFound(p)
    assert exc.path == p
    assert "File not found at" in str(exc)

@pytest.mark.exception
def test_fileformatexception_chain(tmp_path):
    # Dummy-Original-Exception
    orig = ValueError("oops")
    p = tmp_path / "bad.json"
    exc = FileFormatError(p, orig)

    # check if returned path is correct
    assert exc.path == p

    #check if original exception orig is returned correctly
    assert exc.original_exception is orig

    # check msg string
    assert "Invalid format in" in str(exc)

@pytest.mark.exception
def test_filepermission_and_io_error(tmp_path):
    p = tmp_path / "some.json"
    orig_perm = PermissionError("denied")
    perm_exc = FilePermissionError(p, orig_perm)

    assert perm_exc.path == p
    assert perm_exc.original_exception is orig_perm
    assert "No reading rights" in str(perm_exc)

    orig_io = OSError("disk full")
    io_exc = FileIOError(p, orig_io)
    assert io_exc.path == p
    assert io_exc.original_exception is orig_io
    assert "Unexpected I/O error" in str(io_exc)

@pytest.mark.exception
def test_loadererror_direct():
    # LoaderError direkt werfen
    err = LoaderError("something broke")
    assert str(err) == "something broke"

#-------------------------------------------
# Test jsonloader load function
#-------------------------------------------

@pytest.mark.jsonloader
def test_load_single_valid(tmp_path, loader):
    # Generate a valid JSON file, first as a dict
    data = {"foo": 1, "bar": [1,2,3]}
    fp = tmp_path / "a.json"

    # write JSON data with write_text to temporary file a.json
    # json.dumps converts dict data to correct json
    fp.write_text(json.dumps(data), encoding="utf-8")

    result = loader.load("a.json")
    assert result == data

@pytest.mark.jsonloader
def test_load_multiple_valid(tmp_path, loader):
    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    result = loader.load(["a.json", "b.json"])
    assert isinstance(result, dict)
    assert result["a.json"] == a
    assert result["b.json"] == b

@pytest.mark.jsonloader
def test_file_not_specified(loader):
    with pytest.raises(FileNotSpecified):
        loader.load(None)

def test_file_not_found(tmp_path, loader):
    with pytest.raises(FileNotFound) as ei:
        loader.load("nope.json")
    # prüfen, dass das path-Attribut stimmt
    assert ei.value.path == tmp_path / "nope.json"

@pytest.mark.jsonloader
def test_format_error(tmp_path, loader):
    # Schreibe ungültiges JSON
    fp = tmp_path / "bad.json"

    # force error with trailing comma and missing "" for not (instead of "not") for keys
    fp.write_text("{ not: valid, }", encoding="utf-8")

    with pytest.raises(FileFormatError) as ei:
        loader.load("bad.json")
    assert ei.value.path == fp

    # original_exception ist JSONDecodeError
    assert isinstance(ei.value.original_exception, json.JSONDecodeError)

@pytest.mark.jsonloader
def test_permission_error(tmp_path, loader, monkeypatch):
    # Simuliere PermissionError beim read_text
    fp = tmp_path / "p.json"
    fp.write_text("{}", encoding="utf-8")

    def fake_read_text(*args, **kwargs):
        raise PermissionError("denied")
    
    # use monkeypatch to make Path.read_text throw PermissionError by fake_read_text
    # in original loaders.py the json is read with: raw = file_path.read_text(encoding="utf-8")
    # to also replace read_text in the loader.load function during test, we replace read_text
    # with fake_read_text to throw an error. 
    # this monkeypatch replaces for every Path-instance, also in loader.load, the read_text
    # function with fake_read_text
    monkeypatch.setattr(Path, "read_text", fake_read_text)

    with pytest.raises(FilePermissionError) as ei:
        loader.load("p.json")
    assert ei.value.path == fp
    assert isinstance(ei.value.original_exception, PermissionError)

@pytest.mark.jsonloader
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

@pytest.mark.jsonloader
def test_catchall_wraps_unexpected(tmp_path, loader, monkeypatch):
    # Simuliere einen beliebigen Fehler im json.loads
    fp = tmp_path / "u.json"
    fp.write_text("{}", encoding="utf-8")

    def fake_json_loads(_):
        raise RuntimeError("wtf")

    # pytest imports the json module automatically and 
    # automatically splits at the last dot . 
    # then the loads imported from the module json gets replaced with fake_json_loads
    # long version: monkeypatch.setattr(json, "loads", fake_json_loads)
    monkeypatch.setattr("json.loads", fake_json_loads)

    with pytest.raises(Exception) as ei:
        loader.load("u.json")
    # je nach Implementation kann das LoaderError oder OSError sein
    assert "loading" in str(ei.value)

@pytest.mark.jsonloader
def test_load_directory_raises_file_not_found(tmp_path, loader):
        dir_path = tmp_path / "dir"
        dir_path.mkdir()
        with pytest.raises(FileNotFound) as ei:
            loader.load("dir")
        assert ei.value.path == dir_path

@pytest.mark.jsonloader
def test_load_single_valid_with_path(tmp_path):
    """Loader should accept Path objects for filename and base path."""
    data = {"foo": 1}
    fp = tmp_path / "p.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    loader = JSONLoader(base_path=str(tmp_path))
    result = loader.load(Path("p.json"))
    assert result == data


@pytest.mark.jsonloader
def test_load_multiple_valid_with_paths(tmp_path):
    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    loader = JSONLoader(base_path=str(tmp_path))
    result = loader.load([Path("a.json"), Path("b.json")])
    assert isinstance(result, dict)
    assert result["a.json"] == a
    assert result["b.json"] == b

#-------------------------------------------
# Test JSONloader _normalize function
#-------------------------------------------

@pytest.mark.jsonloader
@pytest.mark.normalize_filenames
class TestNormalize:
    def test_normalize_single_string(self, loader):
        """"single filename str converted to List[Path].
        """
        out = loader._normalize("foo.json")
        assert isinstance(out, list)
        assert isinstance(out[0], Path)
        assert out == [Path("foo.json")]

    def test_normalize_list_of_strings(self, loader):
        """A List of str is converted to Path but should get returned unchanged.
        """
        filenames = ["a.json", "b.json", "c.json"]
        out = loader._normalize(filenames)
        # object should stay the same
        assert out == [Path(f) for f in filenames]

    def test_normalize_list_with_non_string(self, loader):
        """Throw ValueError because of non str elements.
        """
        bad = ["a.json", 123, None]
        with pytest.raises(ValueError) as exc:
            loader._normalize(bad)

        msg = str(exc.value)
        assert "str or Path" in msg
        # check if wrong types returned correctly
        assert "<class 'int'>" in msg and "<class 'NoneType'>" in msg

    @pytest.mark.parametrize("bad_input", [
        123,
        None,
        3.14,
        True,
        object(),
    ])
    def test_normalize_invalid_type_raises(self, loader, bad_input):
        """ Test different types (no str/Path, no list) to get a ValueError.
        """
        with pytest.raises(ValueError) as exc:
            loader._normalize(bad_input)
        assert f"got {type(bad_input)}" in str(exc.value)

    
