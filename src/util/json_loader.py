import json
import pandas as pd
 
def readjson(file2read= "car_hardware_config.json"):
    """Einlesen von JSON und Rückgabe als dict"""
    try:
        with open (file2read,"r", encoding="utf-8") as file:
            wasdrinsteht=json.load(file)

        return wasdrinsteht
    except Exception as e:
        raise Exception(e)
    
def save_log_to_file(log_data, filename="fahrt_log.json"):
    """Speichert die Log-Daten in einer JSON-Datei."""
    try:
        with open(filename, "w") as f:
            json.dump(log_data, f, indent=4)
        print(f"Fahrdaten wurden erfolgreich in '{filename}' gespeichert.")
    except Exception as e:
        print(f"Fehler beim Speichern der Log-Datei: {e}")

 