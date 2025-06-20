from pathlib import Path
from typing import Any, Dict, List, Union
import json

# use logging to ensure basic loggin capability
import logging
# import ensures that the bootstrap logger is set up
from util.logger import Logger
# use the bootstrap logger
logger = logging.getLogger(__name__)

# Base class for loader related errors
class LoaderError(Exception):
    """Base class for all related errors 
    """
    pass

class FileNotSpecified(LoaderError):
    """Error is thrown if file to load was not specified
    """
    def __init__(self):
        msg = f"No filename specified"

        # calling __init__ of Exception base class with msg
        super().__init__(msg)

class FileNotFound(LoaderError):
    """Error is thrown if file cannot be found
    """
    def __init__(self, path: Path):
        self.path = path

        msg = f"File not found at {path}"

        # calling __init__ of Exception base class with msg
        super().__init__(msg)

class FileFormatError(LoaderError):
    """Error is thrown if file cannot be parsed.
    """
    def __init__(self, path: Path, original_exception: Exception):

        self.path = path
        self.original_exception = original_exception
        
        msg = f"Invalid format in {path}: {original_exception}"

        # calling __init__ of Exception base class with msg
        super().__init__(msg)

class FilePermissionError(LoaderError):
    """Error is thrown if no access to file is granted.
    """
    def __init__(self, path: Path, original_exception: Exception):
        self.path = path
        self.original_exception = original_exception
        super().__init__(f"No reading rights for {path}: {original_exception}")

class FileIOError(LoaderError):
    """General I/O error when reading files.
    """
    def __init__(self, path: Path, original_exception: Exception):
        self.path = path
        self.original_exception = original_exception
        super().__init__(f"Unexpected I/O error for {path}: {original_exception}")

# Loader-Interface for JSON
class JSONLoader:
    """
    Reads one or more JSON files from a directory.

    Attributes
    ----------
    base_path : pathlib.Path
        Directory containing the JSON file(s).
    filenames : str or list of str or None
        Default filename or list of filenames to load if `load()` is called without arguments.
    """
    def __init__(self, base_path: Union[str, Path],
                 filenames: Union[str, Path, List[Union[str, Path]]] = None) -> None:
        """Create a new ``JSONLoader``.

        Parameters
        ----------
        base_path : str or Path
            Directory from which JSON files will be loaded.
        filenames : str or Path or list, optional
            Optional default filename(s) used when ``load`` is called without an
            argument.
        """
        # normalize base_path to Path
        if isinstance(base_path, Path):
            logger.debug("base_path is already of type Path. assigning")
            self.base_path = base_path
        else:
            logger.debug("base_path is not of type Path. Converting to Path(base_path)")
            self.base_path = Path(base_path)

        # normalize filenames to List[Path] or None
        if filenames is not None:
            self.filenames = self._normalize(filenames)
        else:
            self.filenames = None
            logger.debug("No filenames provided in __init__")

        logger.debug("JSONLoader initialized with base_path=%s filenames=%s",
                     base_path, filenames)

    def _normalize(self, filenames: Union[str, Path, List[Union[str, Path]]]) -> List[Path]:
        """Normalize a filename or list of filenames into a list of `Path` objects.

        Parameters
        ----------
         filenames : str, Path or list
            A single filename or a list of filenames. `Path` objects are
            accepted as well. If a string is provided it is wrapped in a
            one-element list. When a list is provided each element must be a
            `str` or `Path`.
            
        Returns
        -------
        List[Path]
            The normalized and validated list of filenames as `Path` objects.

        Raises
        ------
        ValueError
            If `filenames` is neither a `str`/`Path` nor a list of those
        """
        if isinstance(filenames, (str, Path)):
            logger.debug("filenames is a str or Path. Converting to [Path]")
            return [Path(filenames)]
        
        elif isinstance(filenames, list):
            logger.debug("filenames is a list. normalizing items")

            if not filenames:
                raise ValueError("filenames list must not be empty")
            
            if not all(isinstance(item, (str, Path)) for item in filenames):
                bad_types = {type(item) for item in filenames if not isinstance(item, (str, Path))}
                raise ValueError(
                    f"All items in filenames list must be str or Path, "
                    f"but found types: {bad_types}"
                )
    
            logger.debug("filenames list normalized to Paths")
            return [Path(item) for item in filenames]

        else:
            raise ValueError(
                f"filenames must be str, Path or list; got {type(filenames)}"
            )

    def load(self, 
             filenames: Union[str, Path, List[Union[str, Path]], 
             None] = None) -> Union[Dict[str, Any], Dict[str, Dict[str, Any]]]:
        """
        Load one or more JSON files.

        Parameters
        ----------
        filenames : str, Path, list or None
            Filename or list of filenames to load. If None, `self.filenames` is used.

        Returns
        -------
        dict or dict of dict
            If a single file was loaded, returns the parsed dict from that file.
            Otherwise, returns a mapping from filename to its parsed dict.

        Raises
        ------
        FileNotSpecified
            If no filename was specified.
        FileNotFound
            If any of the specified files does not exist.
        FileFormatError
            If any file contains invalid JSON.
        FilePermissionError
            If any file is not readable due to permission issues.
        FileIOError
            If an unexpected I/O error occurs (e.g., disk full).
        LoaderError
            For any other unexpected errors during loading.
        """
        if filenames is None:
            if self.filenames is None:
                logger.error("No filenames specified for JSONLoader.load()")
                raise FileNotSpecified()
            else:
                # filenames was set in __init__
                files = self.filenames
        else:
            files = self._normalize(filenames)

         # fail early if base_path is not a directory that exists
        if not self.base_path.exists() or not self.base_path.is_dir():
            raise FileNotFound(self.base_path)
        
        results: Dict[str,Any] = {}

        for filename in files:
        
            file_path = self.base_path / filename

            logger.debug("Attempting to read %s", file_path)

            if not file_path.exists() or not file_path.is_file():
                logger.error("File not found: %s", file_path)
                raise FileNotFound(file_path)
            
            try:
                raw = file_path.read_text(encoding="utf-8")
                loaded_json = json.loads(raw)

                logger.debug("Successfully parsed %s (%d bytes)",
                             file_path, len(raw))

            except json.JSONDecodeError as e:               
                logger.error("JSON decode error in %s: %s", file_path, e)
                raise FileFormatError(file_path, e) from e
            
            except PermissionError as e:
                logger.error("Permission denied reading %s: %s", file_path, e)
                raise FilePermissionError(file_path, e) from e
            
            except OSError as e:
                # catch all other file /I/O-errors
                logger.error("I/O error reading %s: %s", file_path, e)
                raise FileIOError(file_path, e) from e

            except Exception as e:
                # all other exceptions land here
                logger.critical("Unexpected error loading %s: %s", file_path, e)
                raise LoaderError(f"Error loading {file_path}: {e}") from e

            results[str(filename)] = loaded_json

        # only one file was specified 
        if len(results) == 1:
            return next(iter(results.values()))
        return results
            