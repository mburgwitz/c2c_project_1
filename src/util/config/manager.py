import os
import threading
import time
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

        # Internal state placeholders
        self._config: Dict[str, Any] = {}
        self._mtimes: Dict[str, float] = {}
        self._stop_event = threading.Event()
        self._watch_thread: Optional[threading.Thread] = None
        self._config_loaded: bool = False

        logger.debug(
            "ConfigManager initialized with path=%s, files=%s, watch=%s",
            self.base_path, self.filenames, self.watch
        )

        # For watch mode, load immediately then start watcher
        if self.watch:
            self.load()
            self._start_watch()

    def load(self) -> Dict[str, Any]:
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
        with self.__class__._lock:
            logger.info("Loading configuration files: %s", self.filenames)
            try:
                from util.config.loaders import JSONLoader
                names = [self.filenames] if isinstance(self.filenames, (str, Path)) else self.filenames
                names = [Path(n) for n in names]
                loader = JSONLoader(self.base_path, names)
                raw = loader.load()
            except Exception as e:
                logger.error("Loading configuration files failed: %s", e)
                raise

            # Merge multiple files into one dict
            files = [self.filenames] if isinstance(self.filenames, (str, Path)) else self.filenames
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
                except Exception as e:
                    logger.error("Schema validation failed: %s", e)
                    raise

            # Apply environment overrides
            merged = self._apply_env_overrides(merged)

            # Record file mtimes for hot-reload checks
            self._mtimes = {}
            for fn in files:
                path = self.base_path / fn
                try:
                    self._mtimes[fn] = path.stat().st_mtime
                except OSError:
                    self._mtimes[fn] = 0.0

            # Cache and mark as loaded
            self._config = merged
            self._config_loaded = True
            logger.info("Configuration loaded successfully")
            return self._config

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
            logger.debug("Applying env override %s = %s", keys, val)
            self._set_deep(cfg, keys, val)
        return cfg

    def _set_deep(self, d: Dict[str, Any], keys: List[str], val: Any) -> None:
        """
        Set a value deep in a nested dict given a list of keys.
        """
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = val

    def get(self, *keys: str) -> Any:
        """
        Retrieve a config value by a sequence of nested keys.

        Example:
            cfg.get("database", "host")
        """
        # Lazy load if not yet loaded
        if not self._config_loaded:
            self.load()
        v = self._config
        for k in keys:
            v = v[k]
        return v

    def as_attr(self) -> Any:
        """
        Return the configuration as an object with attribute-style access.
        """
        # Lazy load if not yet loaded
        if not self._config_loaded:
            self.load()
        return _AttrWrapper(self._config)

    def _start_watch(self) -> None:
        """
        Start the background thread that watches config files for changes.
        """
        if self._watch_thread is not None and self._watch_thread.is_alive():
            return
        self._stop_event.clear()
        self._watch_thread = threading.Thread(target=self._watch_loop, daemon=True)
        self._watch_thread.start()
        logger.info("Started config watch thread (interval=%.2fs)", self.reload_interval)

    def _watch_loop(self) -> None:
        """
        Loop that polls file mtimes and reloads on change.
        """
        while not self._stop_event.is_set():
            time.sleep(self.reload_interval)
            names = [self.filenames] if isinstance(self.filenames, (str, Path)) else self.filenames
            for fname in names:
                path = self.base_path / fname
                try:
                    mtime = path.stat().st_mtime
                except Exception:
                    continue
                if mtime != self._mtimes.get(fname):
                    logger.info("Detected change in %s, reloading config", fname)
                    try:
                        self.load()
                    except Exception:
                        logger.error("Error reloading config after change in %s", fname)
                    break

    def stop_watch(self) -> None:
        """
        Stop the background watch thread.
        """
        if self._watch_thread is None:
            return
        self._stop_event.set()
        self._watch_thread.join()
        logger.info("Stopped config watch thread")


class _AttrWrapper:
    """
    Simple wrapper to access dict keys as attributes.
    """
    def __init__(self, d: Dict[str, Any]) -> None:
        self.__dict__.update(d)
