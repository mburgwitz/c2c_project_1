import json
import pandas as pd
 
def readjson(file2read= "car_hardware_config.json"):
    """
    Read a JSON file and return its contents as a dictionary.

    Parameters
    ----------
    file2read : str, optional
        Path to the JSON file to read (default is "car_hardware_config.json").

    Returns
    -------
    dict
        Parsed JSON content.

    Raises
    ------
    Exception
        If the file cannot be opened or parsed.
    """
    try:
        with open (file2read,"r", encoding="utf-8") as file:
            wasdrinsteht=json.load(file)

        return wasdrinsteht
    except Exception as e:
        raise Exception(e)
    
def save_log_to_file(log_data, filename="fahrt_log.json"):
    """
    Save log data to a JSON file with pretty-print formatting.

    Parameters
    ----------
    log_data : list
        List of log records (e.g., dictionaries) to serialize.
    filename : str, optional
        Destination filename for the JSON output (default is "fahrt_log.json").

    Returns
    -------
    None

    Notes
    -----
    Prints a confirmation message on success or an error message on failure.
    """
    try:
        with open(filename, "w") as f:
            json.dump(log_data, f, indent=4)
        print(f"Fahrdaten wurden erfolgreich in '{filename}' gespeichert.")
    except Exception as e:
        print(f"Fehler beim Speichern der Log-Datei: {e}")

 