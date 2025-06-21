import logging, logging.config
from typing import Any
from pathlib import Path
import threading
from contextlib import contextmanager

# Default local config path and config name
DEFAULT_CONFIG_NAME = "logging.json"
DEFAULT_CONFIG_PATH = Path("./config/")

# -------------------------------------------------------------
# Bootstrap-Fallback: easy StreamHandler,
# for the case that no config was loaded already
# -------------------------------------------------------------

root = logging.getLogger()
if not any(type(h) is logging.StreamHandler for h in root.handlers):
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(name)s %(levelname)s: %(message)s"
    ))
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
# this guarantees a root-logger until the config file for the class
# Logger was read. Enables logging in the loader module

class Logger:
    """ 
    Singleton Logger utility class. Used directly by Logger.get_logger(target)

    Prevents instantiation to ensure only one configuration is loaded.
    On runtime the config file name and path can be updated by "set_config()".
    """
    # Default config file and path
    _instance = None
    _config_name = DEFAULT_CONFIG_NAME
    _config_path = DEFAULT_CONFIG_PATH
    _lock = threading.RLock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 config_name: str = None,
                 config_path: Path = None) -> None:
        
        # Prevent reinitialization of the singleton
        if getattr(self, '_initialized', False):
            return
        
        if config_name is None:
            config_name = self.__class__._config_name
        if config_path is None:
            config_path = self.__class__._config_path

        self._config_name = config_name
        self._config_path = config_path
        self._is_configured = False
        self._initialized = True  # mark init done
        self._last_error = None
        self._failed_attempts = 0

    @classmethod
    def set_config_file(cls, config_name: str, config_path: Path) -> None:
        """
        Override the default logging config file path.
        Resets the loaded-state so the next get_logger triggers reload.

        Parameters
        ----------
        config_file : str
            Pfad zur JSON-Config-Datei (vollständiger Pfad).
        """
        with cls._lock:
            cls._config_name = config_name
            cls._config_path = config_path

            # if a singleton instance already exists, reset its state
            if cls._instance is not None:
                inst = cls._instance
                inst._config_name = config_name
                inst._config_path = config_path
                inst._is_configured = False
                inst._failed_attempts = 0

    @classmethod
    @contextmanager
    def use_config(cls, config_name: str, config_path: Path):
        """Temporarily use another config file within a context."""
        old_name = cls._config_name
        old_path = cls._config_path
        cls.set_config_file(config_name, config_path)
        try:
            yield
        finally:
            cls.set_config_file(old_name, old_path)

    def _configure(self) -> None:
        """
        Load and apply logging configuration once, using current config_name and config_path.
        Falls back to basicConfig on failure.
        """
        with self.__class__._lock:
            if self._is_configured:
                return
            try:
                # use ConfigManager to load the 'logging.json' once
                # import here and not on module layer to avoid circular imports
                from util.config.manager import ConfigManager

                if hasattr(ConfigManager, "reset_instance"):
                    ConfigManager.reset_instance()
                else:
                    ConfigManager._instance = None

                if hasattr(ConfigManager, "get_manager"):
                    cfg = ConfigManager.get_manager(
                        base_path=self._config_path,
                        filenames=self._config_name,
                    )
                else:
                    cfg = ConfigManager(
                        base_path=self._config_path,
                        filenames=self._config_name,
                    )

                config = cfg.load()

                #config = read_and_parse_config(self._config_name, self._config_path)          

                # get basic config looger for deletion
                root = logging.getLogger()

                # delete all global filter
                root.filters.clear()

                # deactivate all (child) logger
                for _, lg in logging.Logger.manager.loggerDict.items():
                    if isinstance(lg, logging.Logger):
                        lg.handlers.clear()
                        lg.disabled = True

                # remove bootstrap handlers for a clean reconfigure with config file
                for h in list(root.handlers):
                    root.removeHandler(h)
                
                # use the loaded config 
                logging.config.dictConfig(config)

                self._is_configured = True
                self._last_error = None

                 # switch ConfigManager logger to configured logger if available
                if hasattr(cfg, "use_logger"):
                    try:
                        cfg.use_logger()
                    except Exception:
                        pass

            except Exception as e:
                # Bootstrap handlers stays active
                failed_path = Path(self._config_path) / self._config_name
                logging.error(
                    f"Failed to load logging configuration '{failed_path}': {e}\n"
                    "Using bootstrap logging."
                )
                self._failed_attempts += 1
                if self._failed_attempts >= 3:
                    self._apply_default_config()

                self._last_error = e

                
    def _apply_default_config(self) -> None:
        """Apply a very small default logging configuration."""
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, logging.StreamHandler):
                h.setFormatter(logging.Formatter(
                    "%(asctime)s %(levelname)s %(name)s: %(message)s"
                ))
        root.setLevel(logging.INFO)
        logging.info("Applied fallback logging configuration")
        self._is_configured = True


    @classmethod
    def get_logger(cls, target: Any) -> logging.Logger:
        """
        Return a configured logger for the given target.

        For a string target, the logger name is the string itself.
        For any other target, the logger name is constructed as
        "{module}.{qualname}", where:
          - module   = target.__module__ (or the class's module)
          - qualname = target.__qualname__ (or the class's __name__)

        Parameters
        ----------
        target : Any
            The target to attach the logger to. Can be:
            - str: used directly as logger name (non-empty)
            - class or instance: uses module and class name
            - function or method: uses module and qualified name

        Returns
        -------
        logging.Logger
            A logger obtained via logging.getLogger(name).

        Raises
        ------
        ValueError
            If `target` is an empty or whitespace-only string.
        """
        # Ensure configuration is loaded once (with current config)
        instance = cls() # calls Logger and instanciates, if not already done
        instance._configure() # check if configuration is already loadad or non

        # target is a str
        if isinstance(target, str):
            if not target.strip():
                raise ValueError("Logger name must not be empty or whitespace only")
            name = target
        else:
            # modul name (String)  
            module = getattr(target, "__module__", target.__class__.__module__)

            # qualified name, e.g. "class: module.Foo", "method: module.Foo.bar", "free function: module.func_name"
            qual_name = getattr(target, "__qualname__", target.__class__.__name__)

            name = f"{module}.{qual_name}"

        return logging.getLogger(name)
