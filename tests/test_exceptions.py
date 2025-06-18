import pytest

from src.util.config.loaders import (
    FileFormatError,
    FileIOError,
    FileNotFound,
    FileNotSpecified,
    FilePermissionError,
    LoaderError
)

# check if attributes like errors, messages and path is received and returned correctly
# uses buildin fixutre tmp_path 

def test_filenotspecified_str():
    e = FileNotSpecified()
    # check instance
    assert isinstance(e, LoaderError)
    # check error message
    assert str(e) == "No filename specified"

def test_filenotfound_attributes_and_msg(tmp_path):
    p = tmp_path / "missing.json"
    exc = FileNotFound(p)
    assert exc.path == p
    assert "File not found at" in str(exc)

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

def test_loadererror_direct():
    # LoaderError direkt werfen
    err = LoaderError("something broke")
    assert str(err) == "something broke"


