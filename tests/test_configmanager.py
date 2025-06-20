import os
import json
import threading
import time
from pathlib import Path

import pytest
from util.config.manager import ConfigManager
from util.config.loaders import FileNotFound

pytestmark = pytest.mark.configmanager

# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_config_manager_and_env():
    """
    Before each test: clear out the ConfigManager singleton so __init__ runs again,
    and snapshot/restore all environment variables so overrides stay isolated.
    """
    # Tear down any existing singleton instance
    if hasattr(ConfigManager, "_instance"):
        ConfigManager._instance = None

    # Snapshot ENV
    original_env = dict(os.environ)
    yield

    # Restore ENV
    os.environ.clear()
    os.environ.update(original_env)

# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_single_file_load(tmp_path):
    """
    Loading a single JSON file should return its contents and support get().
    """
    data = {"a": 1, "b": 2}
    fp = tmp_path / "conf.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "conf.json")
    result = cfg.load()

    assert result == data
    assert cfg.get("a") == 1


def test_multiple_file_merge(tmp_path):
    """
    Loading multiple files merges them; later values override earlier.
    """
    a = {"x": 1, "shared": "from_a"}
    b = {"y": 2, "shared": "from_b"}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    cfg = ConfigManager(tmp_path, ["a.json", "b.json"])
    merged = cfg.load()

    assert merged["x"] == 1
    assert merged["y"] == 2
    assert merged["shared"] == "from_b"


def test_as_attr_access(tmp_path):
    """
    as_attr() should allow attribute-style access to config values.
    """
    data = {"foo": 123, "nested": {"bar": 456}}
    fp = tmp_path / "cfg.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "cfg.json")
    attr = cfg.as_attr()

    assert attr.foo == 123
    assert attr.nested["bar"] == 456


def test_env_override(tmp_path):
    """
    Environment variables override JSON values using CONFIG__ prefix.
    """
    data = {"db": {"host": "default", "port": 3306}}
    fp = tmp_path / "db.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    os.environ["CONFIG__DB__HOST"] = "localhost"
    os.environ["CONFIG__DB__PORT"] = "5432"

    cfg = ConfigManager(tmp_path, "db.json")
    result = cfg.load()

    assert result["db"]["host"] == "localhost"
    assert result["db"]["port"] == "5432"


def test_schema_validation(tmp_path):
    """
    Providing a JSON schema rejects invalid configs.
    """
    data = {"value": 10}
    fp = tmp_path / "val.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    schema = {
        "type": "object",
        "properties": {"value": {"type": "string"}},
        "required": ["value"]
    }
    cfg = ConfigManager(tmp_path, "val.json", schema=schema)

    with pytest.raises(Exception) as exc:
        cfg.load()
    assert "type" in str(exc.value)


def test_singleton_behavior(tmp_path):
    """
    ConfigManager should return the same instance across calls.
    """
    fp1 = tmp_path / "one.json"
    fp1.write_text(json.dumps({"k": 1}), encoding="utf-8")

    c1 = ConfigManager(tmp_path, "one.json")
    assert c1.get("k") == 1

    fp2 = tmp_path / "two.json"
    fp2.write_text(json.dumps({"k2": 2}), encoding="utf-8")

    c2 = ConfigManager(tmp_path, "two.json")
    # Same instance
    assert c1 is c2
    # Without reload, new file not loaded
    with pytest.raises(KeyError):
        c2.get("k2")


def test_hot_reload(tmp_path):
    """
    Hot-reload should detect file changes and update config automatically.
    """
    data = {"val": 1}
    fp = tmp_path / "hot.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "hot.json", watch=True, reload_interval=0.1)
    assert cfg.get("val") == 1

    # Modify file
    time.sleep(0.2)
    fp.write_text(json.dumps({"val": 99}), encoding="utf-8")

    time.sleep(0.3)
    assert cfg.get("val") == 99

    # Stop background watch thread
    cfg.stop_watch()

def test_custom_env_prefix(tmp_path, monkeypatch):
    """
    Setting a custom environment variable prefix works correctly.
    """
    data = {"key": "value"}
    fp = tmp_path / "cfg.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    monkeypatch.setenv("MYCFG__KEY", "new")
    monkeypatch.setenv("CONFIG_ENV_PREFIX", "MYCFG__")

    cfg = ConfigManager(tmp_path, "cfg.json")
    loaded = cfg.load()
    assert loaded["key"] == "new"


def test_missing_base_path_raises(tmp_path):
    """
    Non-existent base_path should raise FileNotFoundError in constructor.
    """
    bad = tmp_path / "no_dir"
    with pytest.raises(FileNotFoundError):
        ConfigManager(bad, "a.json")


def test_load_missing_file(tmp_path):
    """
    Attempting to load an absent JSON file should raise FileNotFoundError.
    """
    cfg = ConfigManager(tmp_path, "absent.json")

    # we have to check for the custom FileNotFound error
    # since it gets raised in JSONloader and gets propagated
    with pytest.raises(FileNotFound):
        cfg.load()


def test_load_invalid_json(tmp_path):
    """
    Invalid JSON syntax should raise a parsing exception.
    """
    fp = tmp_path / "bad.json"
    fp.write_text("{ invalid,,, }", encoding="utf-8")
    cfg = ConfigManager(tmp_path, "bad.json")
    with pytest.raises(Exception) as exc:
        cfg.load()
    assert "Invalid format" in str(exc.value) or isinstance(exc.value, ValueError)


def test_get_lazy_load(tmp_path):
    """
    get() should trigger lazy load on first access.
    """
    fp = tmp_path / "one.json"
    fp.write_text(json.dumps({"x": 42}), encoding="utf-8")
    cfg = ConfigManager(tmp_path, "one.json")
    assert cfg.get("x") == 42


def test_reload_idempotent(tmp_path):
    """
    Calling load() multiple times picks up updated file contents.
    """
    fp = tmp_path / "u.json"
    fp.write_text(json.dumps({"a": 1}), encoding="utf-8")
    cfg = ConfigManager(tmp_path, "u.json")
    first = cfg.load()
    assert first["a"] == 1

    fp.write_text(json.dumps({"a": 2}), encoding="utf-8")
    second = cfg.load()
    assert second["a"] == 2


def test_stop_watch_idempotent(tmp_path):
    """
    stop_watch() can be called multiple times without error.
    """
    fp = tmp_path / "h.json"
    fp.write_text(json.dumps({"v": 1}), encoding="utf-8")
    cfg = ConfigManager(tmp_path, "h.json", watch=True, reload_interval=0.01)
    cfg.stop_watch()
    # second call should not raise
    cfg.stop_watch()

def test_thread_safe_singleton(tmp_path, monkeypatch):
    """Concurrent calls should return the same ConfigManager instance."""
    fp = tmp_path / "t.json"
    fp.write_text("{}", encoding="utf-8")

    monkeypatch.setattr("util.config.loaders.JSONLoader.load", lambda self: {})

    results = []

    def worker():
        cfg = ConfigManager(tmp_path, "t.json")
        cfg.load()
        results.append(cfg)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    assert len(set(id(r) for r in results)) == 1
    ConfigManager._instance = None
