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


def test_multiple_file_merge_paths(tmp_path):
    """
    Loading multiple files using Path objects should merge correctly.
    """
    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    cfg = ConfigManager(tmp_path, [Path("a.json"), Path("b.json")])
    merged = cfg.load()

    assert merged["x"] == 1
    assert merged["y"] == 2


def test_as_attr_access(tmp_path):
    """
    as_attr() should allow attribute-style access to config values.
    """
    data = {"foo": 123, "nested": {"bar": 456}}
    fp = tmp_path / "cfg.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "cfg.json")
    attr = cfg.get(as_attr=True)

    assert attr.foo == 123
    assert attr.nested["bar"] == 456


def test_env_override(tmp_path):
    """
    Environment variables override JSON values using CONFIG__ prefix.
    """
    data = {"db": {"host": "default", "port": 3306, "debug": False, "ratio": 1.0}}
    fp = tmp_path / "db.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    os.environ["CONFIG__DB__HOST"] = "localhost"
    os.environ["CONFIG__DB__PORT"] = "5432"
    os.environ["CONFIG__DB__DEBUG"] = "true"
    os.environ["CONFIG__DB__RATIO"] = "2.5"

    cfg = ConfigManager(tmp_path, "db.json")
    result = cfg.load()

    assert result["db"]["host"] == "localhost"
    assert result["db"]["port"] == 5432
    assert result["db"]["debug"] is True
    assert result["db"]["ratio"] == 2.5


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

    with pytest.raises(Exception):
        cfg.load()


def test_schema_validation_missing_jsonschema(tmp_path, monkeypatch):
    """load() should raise RuntimeError if jsonschema is missing."""
    (tmp_path / "val.json").write_text(json.dumps({"v": 1}), encoding="utf-8")
    schema = {"type": "object"}
    cfg = ConfigManager(tmp_path, "val.json", schema=schema)

    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "jsonschema":
            raise ImportError("no jsonschema")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(RuntimeError):
        cfg.load()


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

def test_apply_env_override_nested_and_types(tmp_path, monkeypatch):
    """_apply_env_overrides handles nested keys and converts values."""
    (tmp_path / "dummy.json").write_text("{}", encoding="utf-8")
    cfg = ConfigManager(tmp_path, "dummy.json")

    base = {"section": {"value": 0}, "flag": False}

    monkeypatch.setenv("CONFIG__SECTION__VALUE", "10")
    monkeypatch.setenv("CONFIG__FLAG", "true")

    out = cfg._apply_env_overrides(base)

    assert out["section"]["value"] == 10
    assert out["flag"] is True


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


def test_start_watch_no_multiple_threads(tmp_path):
    fp = tmp_path / "w.json"
    fp.write_text("{}", encoding="utf-8")
    cfg = ConfigManager(tmp_path, "w.json", watch=False, reload_interval=0.01)
    cfg.load()

    cfg.start_watch()
    first = cfg._watch_thread
    cfg.start_watch()
    second = cfg._watch_thread
    assert first is second
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


def test_path_objects_are_supported(tmp_path):
    """ConfigManager should accept Path objects for filenames."""
    a = {"foo": 1}
    b = {"bar": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    cfg = ConfigManager(tmp_path, [Path("a.json"), Path("b.json")])
    result = cfg.load()

    assert result["foo"] == 1
    assert result["bar"] == 2


def test_env_override_new_keys(tmp_path):
    """Environment variables may introduce new keys not present in JSON."""
    data = {"section": {"existing": "yes"}}
    (tmp_path / "c.json").write_text(json.dumps(data), encoding="utf-8")

    os.environ["CONFIG__SECTION__NEW"] = "added"

    cfg = ConfigManager(tmp_path, "c.json")
    loaded = cfg.load()

    assert loaded["section"]["existing"] == "yes"
    assert loaded["section"]["new"] == "added"


def test_get_manager_returns_singleton(tmp_path):
    """get_manager should return the same instance on subsequent calls."""
    (tmp_path / "a.json").write_text("{}", encoding="utf-8")

    m1 = ConfigManager.get_manager(tmp_path, "a.json")
    m2 = ConfigManager.get_manager(tmp_path, "a.json")

    assert m1 is m2
    assert m1.load() == {}


def test_merge_and_hot_change(tmp_path):
    """Merging configs should update on hot change of a source file."""
    a = {"val": 1}
    b = {"other": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "a.json", watch=True, reload_interval=0.1)
    cfg.load()
    cfg.load(alias="b", filenames="b.json", watch=True)
    cfg.merge_configs("default", "b")

    assert cfg.get("val") == 1
    assert cfg.get("other") == 2

    time.sleep(0.2)
    (tmp_path / "b.json").write_text(json.dumps({"other": 99}), encoding="utf-8")
    time.sleep(0.3)

    assert cfg.get("other") == 99
    cfg.stop_watch()
    cfg.stop_watch("b")


def test_load_with_multiple_base_paths(tmp_path):
    """Files can be located in any of the provided base paths."""
    dir1 = tmp_path / "p1"
    dir2 = tmp_path / "p2"
    dir1.mkdir()
    dir2.mkdir()
    (dir2 / "c.json").write_text(json.dumps({"val": 42}), encoding="utf-8")

    cfg = ConfigManager([dir1, dir2], "c.json")
    data = cfg.load()
    assert data["val"] == 42


def test_load_override_filenames(tmp_path):
    """load() accepts explicit filenames overriding the stored list."""
    (tmp_path / "a.json").write_text(json.dumps({"a": 1}), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"b": 2}), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "a.json")
    cfg.load()

    merged = cfg.load(filenames=["a.json", "b.json"])
    assert merged["a"] == 1 and merged["b"] == 2


def test_reset_instance_stops_watch_thread(tmp_path):
    """reset_instance() should stop any running watch thread."""
    fp = tmp_path / "w.json"
    fp.write_text("{}", encoding="utf-8")

    cfg = ConfigManager(tmp_path, "w.json", watch=True, reload_interval=0.01)

    assert cfg.is_watching()
    thread = cfg._watch_thread

    ConfigManager.reset_instance()

    assert ConfigManager._instance is None
    assert not thread.is_alive()


def test_get_multiple_keys_as_dict(tmp_path):
    """get() should return multiple values as a dict when as_dict is True."""
    data = {"speed": 0, "steering_angle": 90}
    fp = tmp_path / "vals.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "vals.json")
    cfg.load()

    result = cfg.get("speed", "steering_angle", as_dict=True)
    assert result == {"speed": 0, "steering_angle": 90}


def test_add_config_alias_and_merge(tmp_path):
    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "a.json")
    cfg.load()
    cfg.load(alias="b_alias", filenames="b.json")
    cfg.merge_configs("default", "b_alias")

    assert cfg.get("y") == 2
    cfg.load(name="b_alias")
    assert cfg.resolve_alias("b_alias") == "b_alias"


def test_add_config_replace(tmp_path):
    (tmp_path / "one.json").write_text(json.dumps({"v": 1}), encoding="utf-8")
    (tmp_path / "two.json").write_text(json.dumps({"v": 2}), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "one.json")
    cfg.load(alias="temp", filenames="one.json")
    cfg.load(alias="temp", filenames="two.json", merge_into=False)

    assert cfg.get("v", name="temp") == 2

def test_get_multiple_keys_tuple(tmp_path):
    """get() should return multiple values as a tuple when as_dict is False."""
    data = {"a": 1, "b": 2}
    fp = tmp_path / "vals.json"
    fp.write_text(json.dumps(data), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "vals.json")
    cfg.load()

    assert cfg.get("a", "b") == (1, 2)


def test_module_level_load_and_merge(tmp_path):
    from util.config.manager import ConfigManager as cm

    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    cm.reset()
    cm.load(tmp_path, "a.json")
    cm.load(tmp_path, "b.json", alias="b", merge_into=True)

    assert cm.get("x") == 1
    assert cm.get("y") == 2


def test_module_level_load_separate(tmp_path):
    from util.config.manager import ConfigManager as cm

    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    cm.reset()
    cm.load(tmp_path, "a.json")
    cm.load(tmp_path, "b.json", alias="second")

    assert cm.get("x") == 1
    assert cm.get("y", name="second") == 2

def test_remove(tmp_path):
    a = {"x": 1}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps({"y": 2}), encoding="utf-8")

    cfg = ConfigManager(tmp_path, "a.json")
    cfg.load(alias="second", filenames="b.json")
    assert cfg.get("y", name="second") == 2

    cfg.remove("second")

    with pytest.raises(KeyError):
        cfg.get("y", name="second")

def test_classmethod_load_and_get(tmp_path):
    a = {"x": 1}
    b = {"y": 2}
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")

    ConfigManager.reset()
    ConfigManager.load(tmp_path, "a.json")
    ConfigManager.load(tmp_path, "b.json", alias="b")

    assert ConfigManager.get("x") == 1
    assert ConfigManager.get("y", name="b") == 2


def test_get_configs(tmp_path):
    (tmp_path / "one.json").write_text(json.dumps({"v": 1}), encoding="utf-8")
    (tmp_path / "two.json").write_text(json.dumps({"v": 2}), encoding="utf-8")

    ConfigManager.reset()
    ConfigManager.load(tmp_path, "one.json")
    ConfigManager.load(tmp_path, "two.json", alias="two")

    names = set(ConfigManager.get_configs())
    aliases = set(ConfigManager.get_configs(as_alias=True))

    assert names >= {"default", "two"}
    assert "two" in aliases

