import os
import threading
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from util.logger import Logger

logger = Logger.get_logger(__name__)

class ConfigManager:
    """
    Centralized configuration manager that loads and merges JSON config files,
    validates them (optionally), applies environment variable overrides, and
    supports hot-reloading.

    Attributes
    ----------
    base_path : pathlib.Path
        Directory where config files reside.
    filenames : Union[str, Path, List[Union[str, Path]]]
        Filename or ordered list of JSON filenames to load and merge. Strings
        are converted to `Path` objects when loading.
    schema : Optional[Dict[str, Any]]
        JSON Schema used to validate the merged configuration.
    watch : bool
        If True, start a background thread to watch for changes and reload.
    reload_interval : float
        Polling interval in seconds for detecting file changes.
    _config : Dict[str, Any]
        The currently loaded and merged configuration.
    _mtimes : Dict[str, float]
        Last modification times of each config file.
    _watch_thread : threading.Thread
        Background thread for hot-reload.
    _stop_event : threading.Event
        Event to signal the watch thread to stop.
    _config_loaded : bool
        Indicates whether the configuration has been loaded at least once.
    """
    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()

    @classmethod
    def get_manager(
        cls,
        base_path: Union[str, Path],
        filenames: Union[str, Path, List[Union[str, Path]]],
        schema: Optional[Dict[str, Any]] = None,
        watch: bool = False,
        reload_interval: float = 1.0,
    ) -> "ConfigManager":
        """Return singleton instance.

        Parameters
        ----------
        base_path : Union[str, Path]
            Directory where the config files reside.
        filenames : Union[str, Path, List[Union[str, Path]]]
            Filename or list of filenames to load.
        schema : Optional[Dict[str, Any]]
            Optional JSON schema for validation.
        watch : bool
            Whether to start the hot reload watcher.
        reload_interval : float
            Interval used for the watcher.
        """

        return cls(
            base_path,
            filenames,
            schema=schema,
            watch=watch,
            reload_interval=reload_interval,
        )
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance and stop any running watcher."""
        with cls._lock:
            if cls._instance is not None and cls._instance.is_watching():
                cls._instance.stop_watch()
            cls._instance = None

    def __new__(cls,
                base_path: Union[str, Path],
                filenames: Union[str, Path, List[Union[str, Path]]],
                *args, **kwargs
    ) -> 'ConfigManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(
        self,
        base_path: Union[str, Path],
        filenames: Union[str, Path, List[Union[str, Path]]],
        schema: Optional[Dict[str, Any]] = None,
        watch: bool = False,
        reload_interval: float = 1.0
    ) -> None:
        # Prevent reinitialization on subsequent calls
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # Normalize and validate base_path
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            logger.error("Config directory does not exist: %s", self.base_path)
            raise FileNotFoundError(f"Config directory not found: {self.base_path}")

        # Store parameters
        self.filenames = filenames
        self.schema = schema
        self.watch = watch
        self.reload_interval = reload_interval

        # Management structures for multiple configs
        self._states: Dict[str, Dict[str, Any]] = {}
        self._merge_map: Dict[str, List[str]] = {}
        self._active = "default"

        # create default config entry
        self._create_state("default", filenames, schema, watch, reload_interval)

        # Map legacy attributes to active state
        self._sync_from_state("default")


        logger.debug(
            "ConfigManager initialized with path=%s, files=%s, watch=%s",
            self.base_path, self.filenames, self.watch
        )

        # For watch mode, load immediately then start watcher
        if self.watch:
            self.load()
            self.start_watch()

    def _create_state(
        self,
        name: str,
        filenames: Union[str, Path, List[Union[str, Path]]],
        schema: Optional[Dict[str, Any]],
        watch: bool,
        reload_interval: float,
    ) -> None:
        """Create internal state entry for a configuration."""

        if isinstance(filenames, (str, Path)):
            flist = [Path(filenames)]
        else:
            flist = [Path(f) for f in filenames]

        self._states[name] = {
            "filenames": flist,
            "schema": schema,
            "watch": watch,
            "reload_interval": reload_interval,
            "base_config": {},
            "config": {},
            "mtimes": {},
            "watch_thread": None,
            "stop_event": threading.Event(),
            "config_loaded": False,
        }

    def _sync_from_state(self, name: str) -> None:
        """Synchronize public attributes from an internal state."""
        st = self._states[name]
        self.filenames = [str(p) for p in st["filenames"]]
        if len(self.filenames) == 1:
            self.filenames = self.filenames[0]
        self.schema = st["schema"]
        self.watch = st["watch"]
        self.reload_interval = st["reload_interval"]
        self._config = st["config"]
        self._mtimes = st["mtimes"]
        self._watch_thread = st["watch_thread"]
        self._stop_event = st["stop_event"]
        self._config_loaded = st["config_loaded"]

    def _sync_to_state(self, name: str) -> None:
        """Sync the active public attributes back into a state."""
        st = self._states[name]
        if isinstance(self.filenames, list):
            flist = [Path(f) for f in self.filenames]
        else:
            flist = [Path(self.filenames)]
        st["filenames"] = flist
        st["schema"] = self.schema
        st["watch"] = self.watch
        st["reload_interval"] = self.reload_interval
        st["config"] = self._config
        st["base_config"] = st.get("base_config", {})
        st["mtimes"] = self._mtimes
        st["watch_thread"] = self._watch_thread
        st["stop_event"] = self._stop_event
        st["config_loaded"] = self._config_loaded

    # ------------------------------------------------------------------
    # Public API for multiple configs
    # ------------------------------------------------------------------

    def add_config(
        self,
        name: str,
        filenames: Union[str, Path, List[Union[str, Path]]],
        watch: bool = False,
        schema: Optional[Dict[str, Any]] = None,
        reload_interval: Optional[float] = None,
    ) -> None:
        """Add a new named configuration."""
        if name in self._states:
            raise ValueError(f"Config '{name}' already exists")
        if reload_interval is None:
            reload_interval = self.reload_interval
        if schema is None:
            schema = self.schema
        self._create_state(name, filenames, schema, watch, reload_interval)
        if watch:
            self.load(name)
            self.start_watch(name)

    def set_active(self, name: str) -> None:
        """Switch the active configuration."""
        if name not in self._states:
            raise KeyError(name)
        # sync current active state before switching
        self._sync_to_state(self._active)
        self._active = name
        self._sync_from_state(name)

    def merge_configs(self, target: str, source: str) -> Dict[str, Any]:
        """Merge ``source`` config into ``target`` config."""
        if target not in self._states or source not in self._states:
            raise KeyError("unknown config")
        tgt = self._states[target]
        src = self._states[source]
        merged = {**tgt.get("base_config", {}), **src.get("config", {})}
        tgt["config"] = merged
        self._merge_map.setdefault(target, [])
        if source not in self._merge_map[target]:
            self._merge_map[target].append(source)
        if target == self._active:
            self._config = merged
        return merged

    def _apply_merges_for(self, name: str) -> None:
        """Re-apply any recorded merges involving the given config."""
        if name in self._merge_map:
            self._merge_into(name)
        for tgt, sources in self._merge_map.items():
            if name in sources and tgt != name:
                self._merge_into(tgt)

    def _merge_into(self, target: str) -> None:
        base = self._states[target].get("base_config", {})
        merged = dict(base)
        for src in self._merge_map.get(target, []):
            merged.update(self._states[src]["config"])
        self._states[target]["config"] = merged
        if target == self._active:
            self._config = merged

    def load(self, name: Optional[str] = None) -> Dict[str, Any]:
        """
        Load and merge JSON config files, validate, apply ENV overrides.

        Returns
        -------
        Dict[str, Any]
            The merged configuration.

        Raises
        ------
        FileNotFoundError
            If a requested config file doesn’t exist.
        jsonschema.ValidationError
            If a schema is provided and validation fails.
        """
        if name is None:
            name = self._active
        st = self._states[name]

        with self.__class__._lock:
            logger.info("Loading configuration files (%s): %s", name, st["filenames"])
            try:
                from util.config.loaders import JSONLoader
                # names = [self.filenames] if isinstance(self.filenames, (str, Path)) else self.filenames
                # names = [Path(n) for n in names]
                names = st["filenames"]
                loader = JSONLoader(self.base_path, names)
                raw = loader.load()
            except Exception as e:
                logger.error("Loading configuration files failed: %s", e)
                raise

            # Normalize filenames to list of strings
            # if isinstance(self.filenames, (str, Path)):
            #     filenames = [str(self.filenames)]
            # else:
            #     filenames = [str(n) for n in self.filenames]
            filenames = [str(n) for n in names]

            # Merge multiple files into one dict
            files = [filenames] if isinstance(filenames, (str, Path)) else filenames
            if isinstance(raw, dict) and set(raw.keys()) == set(files):
                merged: Dict[str, Any] = {}
                for section in raw.values():
                    merged.update(section)
            else:
                merged = raw

            # Validate against JSON Schema if provided
            if self.schema is not None:
                try:
                    import jsonschema
                    jsonschema.validate(instance=merged, schema=self.schema)
                    logger.debug("Configuration passed JSON Schema validation")
                except ImportError:
                    msg = "jsonschema library required for type validation"
                    logger.error("Schema validation failed: %s", msg)
                    raise RuntimeError(msg)
                except Exception as e:
                    logger.error("Schema validation failed: %s", e)
                    raise

            # Apply environment overrides
            merged = self._apply_env_overrides(merged)

            # Record file mtimes for hot-reload checks
            st["mtimes"] = {}
            for fn in files:
                path = self.base_path / fn
                try:
                    st["mtimes"][fn] = path.stat().st_mtime
                except OSError:
                    st["mtimes"][fn] = 0.0

            # Cache and mark as loaded
            st["base_config"] = merged
            st["config"] = merged.copy()
            st["config_loaded"] = True
            self._apply_merges_for(name)

            if name == self._active:
                self._sync_from_state(name)
            logger.info("Configuration loaded successfully")

            return st["config"]


    def _apply_env_overrides(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override config with environment variables using CONFIG__SECTION__KEY style.
        """
        prefix = os.getenv("CONFIG_ENV_PREFIX", "CONFIG__")
        for var, val in os.environ.items():
            if not var.startswith(prefix):
                continue
            keys = var[len(prefix):].split("__")
            keys = [k.lower() for k in keys]
            try:
                parsed = json.loads(val)
            except Exception:
                parsed = val
            logger.debug("Applying env override %s = %s", keys, parsed)
            typed_val = self._convert_env_value(val)
            self._set_deep(cfg, keys, typed_val)
        return cfg
    
    
    def _convert_env_value(self, value: str) -> Any:
        """
        Convert environment variable strings to int, float or bool when possible.
        """
        lower = value.lower()
        if lower in {"true", "false"}:
            return lower == "true"
        try:
            return int(value)
        except ValueError:
            pass
        try:
            return float(value)
        except ValueError:
            return value
        

    def _set_deep(self, d: Dict[str, Any], keys: List[str], val: Any) -> None:
        """
        Set a value deep in a nested dict given a list of keys.
        """
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = val

    def get(self, *keys: str, name: Optional[str] = None) -> Any:
        """
        Retrieve a config value by a sequence of nested keys.

        Example:
            cfg.get("database", "host")
        """
        # Lazy load if not yet loaded
        if name is None:
            name = self._active
        st = self._states[name]
        if not st["config_loaded"]:
            self.load(name)
        v = st["config"]
        for k in keys:
            v = v[k]
        return v

    def reload(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Explicitly reload the configuration from disk."""
        return self.load(name)
    
    def as_attr(self, name: Optional[str] = None) -> Any:
        """
        Return the configuration as an object with attribute-style access.
        """
        # Lazy load if not yet loaded
        if name is None:
            name = self._active
        st = self._states[name]
        if not st["config_loaded"]:
            self.load(name)
        return _AttrWrapper(st["config"])
    
    # ------------------------------------------------------------------
    # Watcher management
    # ------------------------------------------------------------------

    def is_watching(self, name: Optional[str] = None) -> bool:
        """Return True if the background watch thread is running."""
        if name is None:
            name = self._active
        st = self._states[name]
        th = st.get("watch_thread")
        return th is not None and th.is_alive()

    def start_watch(self, name: Optional[str] = None) -> None:
        """Public method to start the background watch thread."""
        self._start_watch(name)

    def _start_watch(self, name: Optional[str] = None) -> None:
        """
        Start the background thread that watches config files for changes.
        """
        if name is None:
            name = self._active
        st = self._states[name]
        if st["watch_thread"] is not None and st["watch_thread"].is_alive():
            return
        st["stop_event"].clear()
        thread = threading.Thread(target=self._watch_loop, args=(name,), daemon=True)
        st["watch_thread"] = thread
        if name == self._active:
            self._watch_thread = thread
            self._stop_event = st["stop_event"]
        thread.start()
        logger.info("Started config watch thread (interval=%.2fs) for %s", st["reload_interval"], name)

    def _watch_loop(self, name: str) -> None:
        """
        Loop that polls file mtimes and reloads on change.
        """
        st = self._states[name]
        while not st["stop_event"].is_set():
            time.sleep(st["reload_interval"])
            names = st["filenames"]
            for fname in names:
                path = self.base_path / fname
                try:
                    mtime = path.stat().st_mtime
                except Exception:
                    continue
                if mtime != st["mtimes"].get(str(fname)):
                    logger.info("Detected change in %s, reloading config %s", fname, name)
                    try:
                        self.load(name)
                    except Exception:
                        logger.error("Error reloading config %s after change in %s", name, fname)
                    break

    def stop_watch(self, name: Optional[str] = None) -> None:
        """Stop the background watch thread."""
        if name is None:
            name = self._active
        st = self._states[name]
        thread = st.get("watch_thread")
        if thread is None:
            return
        st["stop_event"].set()
        thread.join()
        st["watch_thread"] = None
        if name == self._active:
            self._watch_thread = None
        logger.info("Stopped config watch thread for %s", name)

    # ------------------------------------------------------------------
    # Context manager interface
    # ------------------------------------------------------------------

    def __enter__(self) -> 'ConfigManager':
        if self.watch and not self.is_watching():
            self.start_watch()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.is_watching():
            self.stop_watch()

class _AttrWrapper:
    """
    Simple wrapper to access dict keys as attributes.
    """
    def __init__(self, d: Dict[str, Any]) -> None:
        self.__dict__.update(d)
