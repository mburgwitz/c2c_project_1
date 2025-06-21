import os
import threading
import time
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

class ConfigManager:
    """Centralised configuration handler.

    The manager is implemented as a singleton and keeps track of multiple
    configurations which can be identified either by their given name or by an
    optional alias.  Configurations are loaded from JSON files and may be
    monitored for changes.

    Attributes
    ----------
    base_path : Union[str, Path, list[Union[str, Path]]]
        Directory or list of directories where configuration files reside.
    filenames : Union[str, Path, list[Union[str, Path]]]
        File name or list of files to load.
    schema : dict, optional
        JSON schema used for validation.
    watch : bool, default ``False``
        Start a background thread which reloads changed files automatically.
    reload_interval : float, default ``1.0``
        Polling interval for the watch thread in seconds.
    """
    _instance: Optional['ConfigManager'] = None
    _lock = threading.Lock()

    # ------------------------------------------------------------------
    # Class level convenience API
    # ------------------------------------------------------------------

    @classmethod
    def load(
        cls,
        base_path: Union[str, Path, List[Union[str, Path]]],
        filenames: Union[str, Path, List[Union[str, Path]]],
        *,
        alias: Optional[str] = None,
        merge_into: bool = False,
        watch: bool = False,
        schema: Optional[Dict[str, Any]] = None,
        reload_interval: float = 1.0,
    ) -> Dict[str, Any]:
        """Load a configuration using the singleton instance."""

        if cls._instance is None:
            cls._instance = cls(
                base_path,
                filenames,
                schema=schema,
                watch=watch,
                reload_interval=reload_interval,
            )
            name = "default"
        else:
            name = alias or "extra"
            cls._instance._add_config(
                name,
                filenames,
                watch=watch,
                schema=schema,
                reload_interval=reload_interval,
                alias=alias,
                merge_into="default" if merge_into else None,
                replace=True,
            )

        return cls._instance._load(
            name="default" if merge_into else name,
            watch=watch,
        )

    @classmethod
    def get(
        cls,
        *keys: str,
        name: Optional[str] = None,
        as_dict: bool = False,
        as_attr: bool = False,
    ) -> Any:
        """Return configuration values using the singleton instance."""

        if cls._instance is None:
            raise RuntimeError("No configuration loaded")
        return cls._instance._get(*keys, name=name, as_dict=as_dict, as_attr=as_attr)

    @classmethod
    def remove(cls, name_or_alias: str) -> None:
        """Remove a configuration from the singleton."""

        if cls._instance is None:
            raise RuntimeError("No configuration loaded")
        cls._instance._remove(name_or_alias)

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton and stop any watchers."""
        cls.reset_instance()

    @classmethod
    def get_configs(cls, *, as_alias: bool = False) -> List[str]:
        """Return the list of known configuration names or aliases."""

        if cls._instance is None:
            return []
        if as_alias:
            return list(cls._instance._aliases.keys())
        return list(cls._instance._states.keys())

    @classmethod
    def get_manager(
        cls,
        base_path: Union[str, Path, List[Union[str, Path]]],
        filenames: Union[str, Path, List[Union[str, Path]]],
        schema: Optional[Dict[str, Any]] = None,
        watch: bool = False,
        reload_interval: float = 1.0,
    ) -> "ConfigManager":
        """Return singleton instance.

        Parameters
        ----------
        base_path : Union[str, Path, List[Union[str, Path]]]
            One or multiple directories where the config files reside. If a
            list is provided the directories are searched in order.
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
            if cls._instance is not None:
                try:
                    if cls._instance.is_watching():
                        cls._instance.stop_watch()
                except KeyError:
                    pass
            cls._instance = None

    def __new__(cls,
                base_path: Union[str, Path, List[Union[str, Path]]],
                filenames: Union[str, Path, List[Union[str, Path]]],
                *args, **kwargs
    ) -> 'ConfigManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigManager, cls).__new__(cls)

                # initialize attributes
                cls._instance._states = {}
                cls._instance._merge_map = {}
                cls._instance._aliases = {}
                cls._instance._active = "default"
                cls._instance._initialized = False

                # expose instance level convenience methods
                cls._instance.load = cls._instance._load
                cls._instance.get = cls._instance._get
                cls._instance.remove = cls._instance._remove
                cls._instance.get_configs = cls._instance._get_configs
        return cls._instance


    def __init__(
        self,
        base_path: Union[str, Path, List[Union[str, Path]]],
        filenames: Union[str, Path, List[Union[str, Path]]],
        schema: Optional[Dict[str, Any]] = None,
        watch: bool = False,
        reload_interval: float = 1.0
    ) -> None:
        # Prevent reinitialization on subsequent calls
        if getattr(self, '_initialized', False):
            return

        self._initialized = True

        # prepare core structures
        self._states: Dict[str, Dict[str, Any]] = {}
        self._merge_map: Dict[str, List[str]] = {}
        self._aliases: Dict[str, str] = {}
        self._active = "default"

        import logging
        self.logger = logging.getLogger(__name__)

        # Normalize and validate base paths
        if isinstance(base_path, (str, Path)):
            base_paths = [Path(base_path)]
        else:
            base_paths = [Path(p) for p in base_path]

        for p in base_paths:
            if not p.exists():
                self.logger.error("Config directory does not exist: %s", p)
                raise FileNotFoundError(f"Config directory not found: {p}")

        self.base_paths = base_paths
        # keep the first path for backward compatibility
        self.base_path = base_paths[0]
        self.logger.debug("Base paths set to %s", self.base_paths)

        # Store parameters
        self.filenames = filenames
        self.schema = schema
        self.watch = watch
        self.reload_interval = reload_interval

        # create default config entry
        self._create_state("default", filenames, schema, watch, reload_interval)

        # Map legacy attributes to active state
        self._sync_from_state("default")


        self.logger.debug(
            "ConfigManager initialized with paths=%s, files=%s, watch=%s",
            self.base_paths, self.filenames, self.watch
        )

        # For watch mode, load immediately then start watcher
        if self.watch:
            self._load()
            self.start_watch()

    def use_logger(self) -> None:
        """Switch logger to the project logger after configuration."""
        from util.logger import Logger
        self.logger = Logger.get_logger(__name__)

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
            "file_paths": {},
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
        self._file_paths = st.get("file_paths", {})
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
        st["file_paths"] = getattr(self, "_file_paths", {})
        st["watch_thread"] = self._watch_thread
        st["stop_event"] = self._stop_event
        st["config_loaded"] = self._config_loaded

    # ------------------------------------------------------------------
    # Public API for multiple configs
    # ------------------------------------------------------------------

    def _add_config(
        self,
        name: str,
        filenames: Union[str, Path, List[Union[str, Path]]],
        watch: bool = False,
        schema: Optional[Dict[str, Any]] = None,
        reload_interval: Optional[float] = None,
        *,
        alias: Optional[str] = None,
        merge_into: Optional[str] = None,
        replace: bool = False,
    ) -> None:
        """Add a new named configuration.

        This method is considered internal. External callers should prefer
        :meth:`load` when merely loading additional configuration files.

        Parameters
        ----------
        name : str
            Configuration name or alias to create. Existing entries can be
            replaced by setting ``replace`` to ``True``.
        filenames : str or Path or list
            JSON files comprising the configuration.
        watch : bool, optional
            Enable automatic reloading when files change.
        schema : dict, optional
            JSON schema used for validation.
        reload_interval : float, optional
            Polling interval for the watch thread.
        alias : str, optional
            Alias referring to ``name``.
        merge_into : str, optional
            Merge the created config into another one.
        replace : bool, optional
            Replace an existing configuration with the same name.

        """
        name = self.resolve_alias(name)
        if name in self._states:
            if not replace:
                raise ValueError(f"Config '{name}' already exists")
            
            self._remove(name)

        if reload_interval is None:
            reload_interval = self.reload_interval

        if schema is None:
            schema = self.schema
        self._create_state(name, filenames, schema, watch, reload_interval)

        if alias:
            self._aliases[alias] = name
        self.logger.info("Added configuration '%s' with files %s", name, filenames)

        if watch or merge_into:
            self._load(name=name)
            if watch:
                self.start_watch(name)

        if merge_into is not None:
            target = self.resolve_alias(merge_into)
            self.merge_configs(target, name)

    def set_alias(self, alias: str, target: str) -> None:
        """Create or update an alias for an existing configuration.

        Parameters
        ----------
        alias : str
            Alias name to register.
        target : str
            Name or alias of the configuration that ``alias`` should reference.
            ``target`` must correspond to an existing configuration name and is
            not interpreted as a file path.
        """

        target_name = self.resolve_alias(target)
        if target_name not in self._states:
            self.logger.error("set_alias: unknown target '%s'", target)
            raise KeyError(f"unknown config: {target}")
        
        if self._aliases.get(alias) != target_name:
            self._aliases[alias] = target_name
            self.logger.info("Registered alias '%s' for config '%s'", alias, target_name)


    def merge_configs(self, target: str, source: str) -> Dict[str, Any]:
        """Merge ``source`` configuration into ``target`` configuration."""
        
        target = self.resolve_alias(target)
        source = self.resolve_alias(source)
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
        self.logger.info("Merged config '%s' into '%s'", source, target)
        return merged

    def _remove(self, name_or_alias: str) -> None:
        """Remove a configuration from the manager.

        Parameters
        ----------
        name_or_alias : str
            Name or alias of the configuration to remove.
        """
        name = self.resolve_alias(name_or_alias)
        if name not in self._states:
            raise KeyError(f"unknown config: {name_or_alias}")
        if self.is_watching(name):
            self.stop_watch(name)

        del self._states[name]
        self._merge_map.pop(name, None)
        for sources in self._merge_map.values():
            if name in sources:
                sources.remove(name)

        for alias, target in list(self._aliases.items()):
            if alias == name_or_alias or target == name:
                del self._aliases[alias]

        if self._active == name:
            self._active = "default"
            self._sync_from_state(self._active)

    def _get_configs(self, *, as_alias: bool = False) -> List[str]:
        """Return the list of configuration names or aliases currently loaded."""

        if as_alias:
            return list(self._aliases.keys())
        return list(self._states.keys())
    
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

    def _resolve_file(self, filename: Union[str, Path]) -> Path:
        """Return the full path for ``filename`` searching all base paths."""
        f = Path(filename)
        if f.is_absolute() and f.exists():
            return f
        for base in self.base_paths:
            candidate = base / f
            if candidate.exists():
                return candidate
        # not found - return path in first base for error context
        from util.config.loaders import FileNotFound
        raise FileNotFound(self.base_paths[0] / f)

    def _load(
        self,
        *,
        alias: Optional[str] = None,
        merge_into: Optional[bool] = None,
        name: Optional[str] = None,
        filenames: Optional[Union[str, Path, List[Union[str, Path]]]] = None,
        watch: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Load configuration files and optionally manage alias mappings.

        The configuration to operate on can be selected via ``name`` which may
        also be an alias registered with :meth:`set_alias`.

        Parameters
        ----------
        alias : str, optional
            Alias name to load or create. If the alias already exists the
            behaviour depends on ``merge_into``.
        merge_into : bool, optional
            If ``True`` merge the newly loaded files into the existing config
            referenced by ``alias``. If ``False`` rebuild that configuration
            from scratch. When ``None`` the configuration referenced by
            ``alias`` is simply loaded.
        name : str, optional
            Configuration name to operate on when ``alias`` is not used. When
            merging, this name is used for the temporary source configuration.
        filenames : str, Path or list, optional
            Override the filenames used for loading.
        watch : bool, optional
            Whether the configuration should be watched for changes.

        Returns
        -------
        Dict[str, Any]
            The resulting configuration dictionary.

        Raises
        ------
        FileNotFoundError
            If a requested config file doesn’t exist.
        jsonschema.ValidationError
            If a schema is provided and validation fails.
        """
        if alias is not None:
            if alias in self._aliases or alias in self._states:
                target = self.resolve_alias(alias)
                self.logger.info("Alias '%s' found for config '%s'", alias, target)

                if merge_into is True:
                    src_name = name or f"{target}_merge"
                    self.logger.info(
                        "Merging files %s into alias '%s' using config '%s'",
                        filenames,
                        alias,
                        src_name,
                    )
                    self._add_config(
                        src_name,
                        filenames or self.filenames,
                        alias=alias,
                        watch=watch if watch is not None else False,
                    )
                    self._load(name=src_name)
                    self.merge_configs(target, src_name)
                    return self._states[target]["config"]
                
                elif merge_into is False:
                    self.logger.info(
                        "Replacing config '%s' for alias '%s'", target, alias
                    )
                    cfg_name = name or target
                    self._add_config(
                        cfg_name,
                        filenames or self.filenames,
                        alias=alias,
                        watch=watch if watch is not None else False,
                        replace=True,
                    )
                    return self.load(name=target)
                else:
                    self.logger.debug(
                        "Loading existing config for alias '%s'", alias
                    )
                    return self.load(name=alias, filenames=filenames)
            else:
                cfg_name = name or alias
                self.logger.info("Creating new config '%s' for alias '%s'", cfg_name, alias)
                self._add_config(
                    cfg_name,
                    filenames or self.filenames,
                    replace=True,
                    watch=watch if watch is not None else False,
                )
                return self._load(name=cfg_name)
            
        if name is None:
            name = self._active
        name = self.resolve_alias(name)
        st = self._states[name]

        # allow overriding filenames on this load call
        if filenames is not None:
            if isinstance(filenames, (str, Path)):
                names = [Path(filenames)]
            else:
                names = [Path(f) for f in filenames]
            st["filenames"] = names
        else:
            names = st["filenames"]

        with self.__class__._lock:
            self.logger.info("Loading configuration files (%s): %s", name, [str(n) for n in names])
            from util.config.loaders import JSONLoader
            sections: Dict[str, Any] = {}
            st["file_paths"] = {}

            for fname in names:
                try:
                    path = self._resolve_file(fname)
                except Exception as e:
                    self.logger.error("Failed to resolve %s: %s", fname, e)
                    raise

                self.logger.info("Loading %s", path)
                loader = JSONLoader(path.parent, path.name)
                try:
                    data = loader.load()
                except Exception as e:
                    self.logger.error("Loading configuration file %s failed: %s", path, e)
                    raise
                sections[str(fname)] = data
                st["file_paths"][str(fname)] = path

            # Merge multiple files into one dict
            if len(sections) == 1:
                merged = next(iter(sections.values()))
            else:
                merged = {}
                for sec in sections.values():
                    merged.update(sec)

            # Validate against JSON Schema if provided
            if self.schema is not None:
                try:
                    import jsonschema
                    jsonschema.validate(instance=merged, schema=self.schema)
                    self.logger.debug("Configuration passed JSON Schema validation")
                except ImportError:
                    msg = "jsonschema library required for type validation"
                    self.logger.error("Schema validation failed: %s", msg)
                    raise RuntimeError(msg)
                except Exception as e:
                    self.logger.error("Schema validation failed: %s", e)
                    raise

            # Apply environment overrides
            merged = self._apply_env_overrides(merged)

            # Record file mtimes for hot-reload checks
            st["mtimes"] = {}
            for fn, path in st["file_paths"].items():
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
            self.logger.info("Configuration loaded successfully")

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
            self.logger.debug("Applying env override %s = %s", keys, parsed)
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

    def resolve_alias(self, name: str) -> str:
        """Return the canonical config name for an alias."""
        return self._aliases.get(name, name)
    

    def _get(
        self,
        *keys: str,
        name: Optional[str] = None,
        as_dict: bool = False,
        as_attr: bool = False,
    ) -> Any:
        """
        Retrieve a config value by a sequence of nested keys.

        Example:
            cfg = ConfigManager.get_manager('config', 'car.json')
            angle = cfg.get('steering_angle')

        A ``KeyError`` is raised if any key is missing in the loaded
        configuration. When ``as_attr`` is ``True`` the complete configuration is
        returned wrapped in an object that allows attribute style access.
        """
        # Lazy load if not yet loaded
        if name is None:
            name = self._active
        name = self.resolve_alias(name)
        st = self._states[name]
        if not st["config_loaded"]:
            self.load(name=name)
        cfg = st["config"]

        if as_attr and keys:
            raise ValueError("as_attr=True cannot be used together with keys")

        if not keys:
            return _AttrWrapper(cfg) if as_attr else cfg

        if len(keys) > 1:
            if as_dict:
                return {k: cfg[k] for k in keys}
            return tuple(cfg[k] for k in keys)

        v = cfg
        for k in keys:
            v = v[k]
        return v

    def reload(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Explicitly reload the configuration from disk."""
        return self._load(name=name)
    

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
        name = self.resolve_alias(name)
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
        self.logger.info("Started config watch thread (interval=%.2fs) for %s", st["reload_interval"], name)

    def _watch_loop(self, name: str) -> None:
        """
        Loop that polls file mtimes and reloads on change.
        """
        st = self._states[name]
        while not st["stop_event"].is_set():
            time.sleep(st["reload_interval"])
            names = st["filenames"]
            for fname in names:
                path = st.get("file_paths", {}).get(str(fname))
                if path is None:
                    try:
                        path = self._resolve_file(fname)
                        st.setdefault("file_paths", {})[str(fname)] = path
                    except Exception:
                        continue
                try:
                    mtime = path.stat().st_mtime
                except Exception as e:
                    self.logger.error(
                        "Error reading mtime for %s while watching config %s: %s",
                        path,
                        name,
                        e,
                    )
                    continue
                if mtime != st["mtimes"].get(str(fname)):
                    self.logger.info("Detected change in %s, reloading config %s", fname, name)
                    try:
                        self._load(name=name)
                    except Exception:
                        self.logger.error("Error reloading config %s after change in %s", name, fname)
                    break

    def stop_watch(self, name: Optional[str] = None) -> None:
        """Stop the background watch thread."""
        if name is None:
            name = self._active
        name = self.resolve_alias(name)
        st = self._states[name]
        thread = st.get("watch_thread")
        if thread is None:
            return
        st["stop_event"].set()
        thread.join()
        st["watch_thread"] = None
        if name == self._active:
            self._watch_thread = None
        self.logger.info("Stopped config watch thread for %s", name)

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
    """Wrapper to access dictionary keys as attributes.

    This implementation recursively wraps nested dictionaries so that
    ``cfg.foo.bar`` works for any depth. The object still behaves like a
    mapping via ``__getitem__`` for backward compatibility.
    """
    def __init__(self, d: Dict[str, Any]) -> None:
        for key, value in d.items():
            if isinstance(value, dict):
                value = _AttrWrapper(value)
            self.__dict__[key] = value

    def __getitem__(self, item: str) -> Any:
        return self.__dict__[item]
