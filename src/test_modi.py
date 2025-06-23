import click
import time
import json
from soniccar import SonicCar

def save_log_to_file(log_data, filename="fahrt_log.json"):
    """Speichert die Log-Daten in einer JSON-Datei."""
    try:
        with open(filename, "w") as f:
            json.dump(log_data, f, indent=4)
        print(f"Fahrdaten wurden erfolgreich in '{filename}' gespeichert.")
    except Exception as e:
        print(f"Fehler beim Speichern der Log-Datei: {e}")


@click.command()
@click.option('--modus', '--m', type=int, required=True, help="Wähle den zu testenden Fahrmodus (3 oder 4).")
def main(modus):
    """
    Hauptprogramm zum Testen der Fahrmodi der SonicCar-Klasse.
    """
    print("-- TESTPROGRAMM FÜR SONICCAR --")
    
    # Wartezeit vor dem Start, um das Auto zu positionieren
    print("Stelle das Auto auf. Der Test startet in 5 Sekunden...")
    time.sleep(5)
    
    car = SonicCar()
    
    try:
        if modus == 1:
            print("\n--- Starte Fahrmodus 1: Vorwärtsfahrt Stop und Rückwärtsfahrt ---")
            car.fahrmodus1(geschwindigkeit=30,fahrzeit=4)
            print("--- Fahrmodus 1 beendet ---")

        elif modus == 2:
            print("\n--- Starte Fahrmodus 2: Vorwärtsfahrt Kreisfahrt und Return ---")
            car.fahrmodus2(geschwindigkeit=30,lenkwinkel=135)
            car.fahrmodus2(geschwindigkeit=30,lenkwinkel=45)
            print("--- Fahrmodus 2 beendet ---")

        elif modus == 3:
            print("\n--- Starte Fahrmodus 3: Vorwärtsfahrt bis Hindernis ---")
            # Parameter: Geschwindigkeit 30, Stopp-Distanz 15 cm
            car.drive_until_obstacle(speed=30, stop_distance=15)
            print("--- Fahrmodus 3 beendet ---")
            
        elif modus == 4:
            print("\n--- Starte Fahrmodus 4: Erkundungstour ---")
            # Parameter: Geschwindigkeit 30, Stopp-Distanz 20 cm, Dauer 45 Sekunden
            car.explore(speed=30, stop_distance=20, duration_s=45)
            print("--- Fahrmodus 4 beendet ---")
            
        else:
            print(f"Fehler: Modus {modus} ist unbekannt. Wähle 1 - 4.")
            return

    except KeyboardInterrupt:
        print("\nTest durch Benutzer abgebrochen.")
    
    finally:
        # Sicherstellen, dass das Auto am Ende immer stoppt
        print("Sicherheitsstopp wird durchgeführt.")
        car.stop()
        
        # Log-Daten speichern
        if car.log:
            save_log_to_file(car.log)
        else:
            print("Keine Log-Daten zum Speichern vorhanden.")

if __name__ == '__main__':
    # Beispielaufrufe über die Kommandozeile:
    # python test_modi.py --modus 3
    # python test_modi.py -m 4
    main()