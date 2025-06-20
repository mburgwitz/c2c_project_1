import logging
import threading

# used to reload util.logger module from scratch with importlib.reload
import importlib
import pytest

from pathlib import Path

# keep reference to module to reload it
import util.logger as logger_mod
# now pull the singleton Logger class
from util.logger import Logger, DEFAULT_CONFIG_NAME, DEFAULT_CONFIG_PATH

pytestmark = pytest.mark.logger

# -----------------------------------------------------------------------------
# Fixture: each test runs with a fresh logging and singleton state
# -----------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def reset_logging_and_singleton():
    """ Reset Logger instance and remove StreamHandler from root
    """
    # Reset the Logger singleton
    Logger._instance = None # wipe existing Logger instance 
    Logger._config_name = DEFAULT_CONFIG_NAME
    Logger._config_path = DEFAULT_CONFIG_PATH

    # Reset ConfigManager singleton to avoid cross-test pollution
    from util.config.manager import ConfigManager
    if hasattr(ConfigManager, "_instance"):
        ConfigManager._instance = None

    # Remove only native StreamHandlers (keep pytest's capture handlers)
    # fetch root logger
    root = logging.getLogger()

    # iterate though handler and only wipe remove StreamHandler
    # this is to leave pytest own LogCaptureHandler intact so that caplog can still work
    for handler in list(root.handlers):
        if type(handler) is logging.StreamHandler:
            root.removeHandler(handler)
    
    # 'pause' between 'setup' (above) and 'teardown' (below)
    # after a test finishes, pytest resumes here and runs the removal steps
    # might be removed, but this double checks that no StreamHandler remains after a test
    yield
    # Clean up after test
    for handler in list(root.handlers):
        if type(handler) is logging.StreamHandler:
            root.removeHandler(handler)

# -----------------------------------------------------------------------------
# Helper: reload the logger module so bootstrap basic config runs again
# -----------------------------------------------------------------------------
def reload_logger_module():
    """ Remove native StreamHandlers before reloading.
        Every import of logger.py runs its bootstrap code. To test this bootstrap logic,
        we need a fresh reload.
    """
    # same logic as in fixture
    root = logging.getLogger()
    for handler in list(root.handlers):
        if type(handler) is logging.StreamHandler:
            root.removeHandler(handler)

    # drop old module object an re-execute bootstrap code from scratch
    importlib.reload(logger_mod)
    #overwrite old 'name' of previously imported logger
    globals()['Logger'] = logger_mod.Logger
    return logging.getLogger()

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_bootstrap_stream_handler_attached():
    """
    On first import, exactly one native StreamHandler should be attached with basic config.
    """
    # Clear existing handlers and reload module
    # Here we also want to purge pytests handler, since it is not needed in this test
    # that is why reload_logger_module is NOT used
    root = logging.getLogger()
    for handler in list(root.handlers):
        # remove ALL handler, no safeguard for pytest handler
        root.removeHandler(handler)
    importlib.reload(logger_mod)
    root = logging.getLogger()

    # Count only pure StreamHandler instances
    handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
    assert len(handlers) == 1
    assert root.level == logging.DEBUG


def test_get_logger_string_and_dictconfig(monkeypatch):
    """
    get_logger('name') should instantiate JSONLoader and call dictConfig once.
    """
    root = reload_logger_module()

    # Spy on dictConfig
    called = {}
    def fake_dictConfig(cfg):
        called['cfg'] = cfg
    # replace module function dictConfig
    monkeypatch.setattr(logging.config, 'dictConfig', fake_dictConfig)

    # Patch JSONLoader in util.config.loaders
    class DummyLoader:
        def __init__(self, *, base_path, filenames):
            called['path'] = base_path
            called['name'] = filenames
        def load(self):
            return {
                "version": 1,
                "disable_existing_loggers": False,
                "handlers": {},
                "loggers": {}
            }
    monkeypatch.setattr(
        'util.config.manager.ConfigManager',
        DummyLoader,
        raising=True
    )

    log = Logger.get_logger("myapp")
    # dictConfig was called exactly once
    assert 'cfg' in called
    # JSONLoader was constructed with DEFAULT_CONFIG_PATH and DEFAULT_CONFIG_NAME
    # convert the string DEFAULT_CONFIG_PATH to Path(DEFAULT_CONFIG_PATH)
    # because logger uses ConfigManager that converts all path str to Path
    assert called['path'] == DEFAULT_CONFIG_PATH
    assert called['name'] == DEFAULT_CONFIG_NAME
    assert isinstance(log, logging.Logger)
    assert log.name == "myapp"


def test_empty_string_name_raises():
    """
    Empty or whitespace-only logger names should raise ValueError.
    """
    reload_logger_module()
    with pytest.raises(ValueError):
        Logger.get_logger("   ")


def test_get_logger_class_vs_instance_name(monkeypatch):
    """
    Class and instance should produce different logger names.
    """
    reload_logger_module()

    # Patch JSONLoader to avoid real file loading
    class DummyLoader:
        def __init__(self, *args, **kwargs): pass
        def load(self):
            return {"version":1, "disable_existing_loggers":False,
                    "handlers":{}, "loggers":{}}
    monkeypatch.setattr(
        'util.config.loaders.JSONLoader',
        DummyLoader,
        raising=True
    )

    class Foo: pass
    foo = Foo()

    log_class = Logger.get_logger(Foo)
    log_inst  = Logger.get_logger(foo)

    # Instance logger ends with .Foo
    assert log_inst.name.endswith(".Foo")
    # They should not be identical
    assert log_class.name != log_inst.name


def test_configure_idempotent(monkeypatch):
    """
    Multiple get_logger calls should invoke dictConfig only once.
    """
    reload_logger_module()
    calls = []
    monkeypatch.setattr(logging.config, 'dictConfig', lambda cfg: calls.append(cfg))

    class DummyLoader:
        def __init__(self, *args, **kwargs): pass
        def load(self):
            return {"version":1, "disable_existing_loggers":False,
                    "handlers":{}, "loggers":{}}
    monkeypatch.setattr('util.config.loaders.JSONLoader', DummyLoader, raising=True)

    Logger.get_logger("one")
    Logger.get_logger("two")
    assert len(calls) == 1


def test_set_config_file_forces_reload(monkeypatch):
    """
    set_config_file should update the path and name for the next configuration load.
    """
    reload_logger_module()

    # First loader
    monkeypatch.setattr('util.config.manager.ConfigManager', lambda bp, fn: type("X",(),{"load":lambda s:{}})(), raising=True)
    Logger.get_logger("initial")

    # Override config file settings
    new_path = "/tmp/logcfg"
    new_name = "foo.json"
    Logger.set_config_file(new_name, new_path)

    got = {}
    class LoaderCM:
            def __init__(self, base_path, filenames):
                got['base_path'] = base_path
                got['filenames'] = filenames
            def load(self): return {"version":1,"disable_existing_loggers":False,"handlers":{},"loggers":{}}
    monkeypatch.setattr('util.config.manager.ConfigManager', LoaderCM, raising=True)

    Logger.get_logger("after")
    assert Path(got['base_path']) == Path(new_path)
    assert got['filenames']       == new_name


def test_loader_exception_does_not_remove_bootstrap(monkeypatch, caplog):
    """
    If JSONLoader.load raises an exception, the bootstrap StreamHandler should remain.
    """
    root = reload_logger_module()

    class BadLoader:
        def __init__(self, *args, **kwargs): pass
        def load(self):
            raise RuntimeError("boom")
    monkeypatch.setattr('util.config.loaders.JSONLoader', BadLoader, raising=True)

    caplog.set_level(logging.ERROR)
    Logger.get_logger("fail")
    assert "Failed to load logging configuration" in caplog.text

    # Bootstrap StreamHandler is still present
    handlers = [h for h in root.handlers if type(h) is logging.StreamHandler]
    assert handlers, "Expected bootstrap StreamHandler to remain"

    # configuration flag stays False
    assert not Logger._instance._is_configured

    # next call should attempt configuration again
    calls = []
    class GoodLoader:
        def __init__(self, *args, **kwargs): pass
        def load(self):
            return {"version":1, "disable_existing_loggers":False,
                    "handlers":{}, "loggers":{}}
    monkeypatch.setattr('util.config.loaders.JSONLoader', GoodLoader, raising=True)
    monkeypatch.setattr(logging.config, 'dictConfig', lambda cfg: calls.append(cfg))

    Logger.get_logger("retry")
    assert len(calls) == 1
    assert Logger._instance._is_configured

def test_thread_safe_logger_singleton(monkeypatch):
    """Concurrent get_logger calls should configure only once."""
    reload_logger_module()

    call_count = 0

    class DummyCM:
        def __init__(self, *a, **k):
            pass
        def load(self):
            nonlocal call_count
            call_count += 1
            return {"version":1,"disable_existing_loggers":False,"handlers":{},"loggers":{}}

    monkeypatch.setattr('util.config.manager.ConfigManager', DummyCM, raising=True)
    monkeypatch.setattr(logging.config, 'dictConfig', lambda cfg: None)

    instances = []

    def worker():
        Logger.get_logger("x")
        instances.append(Logger._instance)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(set(id(i) for i in instances)) == 1
    assert call_count == 1
    Logger._instance = None