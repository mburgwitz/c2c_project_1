import logging, logging.config
from typing import Any
from pathlib import Path

from .config_reader import read_and_parse_config

# Default lokaler Pfad zur Logging-Konfiguration
DEFAULT_CONFIG_NAME = "logging.json"
DEFAULT_CONFIG_PATH = "./config/"


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
            cls._instance = super(Logger, cls).__new__(cls, *args, **kwargs)
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
        cls._is_configured = False

    def _configure(self) -> None:
        """
        Load and apply logging configuration once, using current config_name and config_path.
        Falls back to basicConfig on failure.
        """
        if self._is_configured:
            return
        try:
            config = read_and_parse_config(self._config_name, self._config_path)
            logging.config.dictConfig(config)
        except Exception as e:
            logging.basicConfig(level=logging.INFO)
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
