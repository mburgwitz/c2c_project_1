import logging, logging.config
from typing import Any
from pathlib import Path

# Default local config path and config name
DEFAULT_CONFIG_NAME = "logging.json"
DEFAULT_CONFIG_PATH = "./config/"

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

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            #cls._instance = super(Logger, cls).__new__(cls, *args, **kwargs)
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self,
                 config_name: str = 'logging.json',
                 config_path: str = './config/') -> None:
        
        # Prevent reinitialization of the singleton
        if getattr(self, '_initialized', False):
            return
        
        self._config_name = config_name
        self._config_path = config_path
        self._is_configured = False
        self._initialized = True  # mark init done

    @classmethod
    def set_config_file(cls, config_name: str, config_path: str) -> None:
        """
        Override the default logging config file path.
        Resets the loaded-state so the next get_logger triggers reload.

        Parameters
        ----------
        config_file : str
            Pfad zur JSON-Config-Datei (vollständiger Pfad).
        """
        cls._config_name = config_name
        cls._config_path = config_path

        # if a singleton instance already exists, reset its state
        if cls._instance is not None:
            inst = cls._instance
            inst._config_name = config_name
            inst._config_path = config_path
            inst._is_configured = False

    def _configure(self) -> None:
        """
        Load and apply logging configuration once, using current config_name and config_path.
        Falls back to basicConfig on failure.
        """
        if self._is_configured:
            return
        try:
            # use ConfigManager to load the 'logging.json' once
            # import here and not on module layer to avoid circular imports
            from util.config.manager import ConfigManager

            cfg = ConfigManager(
                base_path=self._config_path,
                filenames=self._config_name
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

        except Exception as e:
            # Bootstrap handlers stays active
            logging.error(f"Failed to load logging configuration '{self._config_path + self._config_name}': {e}")
        finally:
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
