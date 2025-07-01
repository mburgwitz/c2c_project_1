'''
    Information: Klasse, die BaseCar um Infrarot- und Ultraschallsensorik erweitert.
    File name: sensorcar.py
    Usage: Ermöglicht Linienverfolgung und Hinderniserkennung.
'''
from basecar import BaseCar
from basisklassen import Ultrasonic, Infrared
import time
import numpy as np
import json

import util.json_loader as loader

class SensorCar(BaseCar):
    '''
    Die SensorCar-Klasse erbt von BaseCar und erweitert diese um die Fähigkeit,
    sowohl den Ultraschallsensor zur Hinderniserkennung als auch die
    Infrarotsensoren zur Linienverfolgung zu nutzen.
    
    Die Daten beider Sensortypen werden im Fahrtenbuch (log) aufgezeichnet.

    Erbt von:
        BaseCar

    Neue Methoden:
        get_distance() - Gibt die Distanz des Ultraschallsensors zurück.
        get_line_status() - Gibt den digitalen Status der Infrarotsensoren zurück.
        line_follower(...) - Fährt entlang einer Linie (Fahrmodus 5).
        advanced_line_follower(...) - Folgt einer Linie auch bei scharfen Kurven (Fahrmodus 6).
        line_follower_with_obstacle_avoidance(...) - Kombinierte Linienverfolgung mit Hindernisstop (Fahrmodus 7).
    '''
    HARDWARE_CONFIG_FILE = "/home/pi/Desktop/git/c2c_project_1/src/config/car_hardware_config.json"

    def __init__(self, steering_angle: int = 90, speed: int = 0):
        '''
        Konstruktor für die SensorCar-Klasse.

        Initialisiert die übergeordnete BaseCar-Klasse sowie die
        Ultraschall- und Infrarotsensoren.
        '''
        # 1. Initialisierung der Basisklasse (Motoren etc.)
        super().__init__(steering_angle, speed)

        # 2. Instanziierung der Sensoren
        self.__us = Ultrasonic()
        self.__ir = Infrared()
        
        self.reference_ground()  # Optional: Referenzwerte der Infrarotsensoren setzen   
             
        # HINWEIS: Für optimale Ergebnisse sollten die Infrarotsensoren kalibriert werden.
        # Rufen Sie vor dem Start der Fahrmodi bei Bedarf self.__ir.cali_references() auf.
        # Alternativ können Sie die Referenzwerte manuell setzen:
        cfg = loader.readjson(SensorCar.HARDWARE_CONFIG_FILE)
        #self.__ir.set_references([28, 28, 28, 28, 28])        
        self.__ir.set_references(cfg["infrared_reference"])        
         

        print("SensorCar wurde initialisiert und ist bereit.")

    # --- Hilfsmethoden für Sensoren ---

    def get_distance(self) -> int:
        '''
        Fragt den Ultraschallsensor ab und gibt die Distanz in cm zurück.
        Fehlerwerte des Sensors (<0) werden als sehr große Distanz (999) interpretiert,
        um die Logik in den Fahrmodi zu vereinfachen.

        Returns:
            int: Gemessene Distanz in cm oder 999 bei einem Sensorfehler.
        '''
        distance = self.__us.distance()
        return 999 if distance < 0 else distance

    def get_line_status(self) -> list:
        '''
        Liest die digitalen Werte der 5 Infrarotsensoren.
        Eine '1' bedeutet, der Sensor erkennt die Linie.
        Eine '0' bedeutet, der Sensor erkennt den Hintergrund.

        Returns:
            list: Eine Liste mit 5 Elementen (0 oder 1), z.B. [0, 0, 1, 0, 0].
        '''
        return self.__ir.read_digital()

    # --- Überschriebene Methoden für die Datenaufzeichnung ---

    def _log_status(self):
        '''
        Erweitert die Protokollierung um die Daten des Ultraschall- und Infrarotsensors.
        Diese Methode wird bei jeder Aktion (drive, stop) aufgerufen.
        '''
        status_record = {
            "timestamp": time.time(),
            "speed": self.speed,
            "steering_angle": self.steering_angle,
            "direction": self.direction,
            "distance_cm": self.get_distance(),
            "line_sensors": self.get_line_status()
        }
        self.log.append(status_record)
        # print(status_record) # Für Echtzeit-Debugging einkommentieren

    def drive(self, speed: int = None, angle: int = None):
        '''
        Überschreibt die drive-Methode von BaseCar, um die erweiterte Datenaufzeichnung hinzuzufügen.
        '''
        super().drive(speed, angle)
        self._log_status()

    def stop(self):
        '''
        Überschreibt die stop-Methode von BaseCar, um die erweiterte Datenaufzeichnung hinzuzufügen.
        '''
        super().stop()
        self.__us.stop()
        self._log_status()

    # --- Implementierung der geforderten Fahrmodi ---
    #def line_follower(self, speed: int = 25, Kp: float = 15.0):
    def line_follower(self, speed: int = 30, Kp: float = 15.0):
        '''
        Fahrmodus 5: Linienverfolgung mit einem Proportionalregler.
        Das Auto folgt einer Linie und stoppt, wenn diese endet.

        Args:
            speed (int): Die Grundgeschwindigkeit des Autos.
            Kp (float): Die Verstärkungskonstante des P-Reglers.
                        Ein höherer Wert führt zu stärkeren Lenkkorrekturen.
        '''
        print(f"Fahrmodus 5: Starte Linienverfolgung mit Geschwindigkeit {speed}.")
        
        # Gewichte für die Sensoren: links = negativ, rechts = positiv
        sensor_weights = np.array([-2, -1, 0, 1, 2])

        while True:
            line_status = np.array(self.get_line_status())

            # Bedingung zum Stoppen: Linie verloren (alle Sensoren auf 0)
            if np.sum(line_status) == 0:
                print("Linie verloren oder Ende erreicht. Stoppe.")
                self.stop()
                break

            # Berechnung des Fehlers mit P-Regler-Logik
            # error < 0: Linie ist links vom Zentrum
            # error > 0: Linie ist rechts vom Zentrum
            # error = 0: Linie ist perfekt im Zentrum
            error = np.sum(line_status * sensor_weights)
            
            # Berechnung der Lenkkorrektur
            correction = Kp * error
            
            # Setzen des neuen Lenkwinkels
            steering_angle = 90 + correction
            
            self.drive(speed, steering_angle)
            
            time.sleep(0.01) # Kurze Pause zur Stabilisierung


    def advanced_line_follower(self, speed: int = 20, Kp: float = 20.0, duration_s: int = 60):
        '''
        Fahrmodus 6: Erweiterte Linienverfolgung für scharfe Kurven.
        Wenn die Linie verloren geht, sucht das Auto in der letzten bekannten Richtung weiter.

        Args:
            speed (int): Die Grundgeschwindigkeit.
            Kp (float): Die Verstärkungskonstante des P-Reglers.
            duration_s (int): Die maximale Fahrzeit in Sekunden.
        '''
        print(f"Fahrmodus 6: Starte erweiterte Linienverfolgung für {duration_s}s.")
        start_time = time.time()
        
        sensor_weights = np.array([-2, -1, 0, 1, 2])
        last_error = 0.0

        while time.time() - start_time < duration_s:
            line_status = np.array(self.get_line_status())

            if np.sum(line_status) > 0:
                # Linie ist sichtbar -> normale Regelung
                error = np.sum(line_status * sensor_weights)
                last_error = error # Letzten Fehler merken
                
                correction = Kp * error
                steering_angle = 90 + correction
                
                self.drive(speed, steering_angle)
            else:
                # Linie ist verloren -> Suchmanöver starten
                print(f"Linie verloren, suche basierend auf letztem Fehler ({last_error:.2f}).")
                if last_error < 0: # Linie war zuletzt links
                    self.drive(speed, self.MIN_STEERING_ANGLE) # Scharf links lenken
                else: # Linie war zuletzt rechts oder mittig
                    self.drive(speed, self.MAX_STEERING_ANGLE) # Scharf rechts lenken
            
            time.sleep(0.02)
        
        print("Fahrzeit beendet.")
        self.stop()

    def line_follower_with_obstacle_avoidance(self, speed: int = 25, Kp: float = 15.0, stop_distance: int = 15):
        '''
        Fahrmodus 7: Kombination aus Linienverfolgung und Hinderniserkennung.
        Das Auto folgt der Linie, bis ein Hindernis in Reichweite kommt, und stoppt dann.

        Args:
            speed (int): Die Grundgeschwindigkeit.
            Kp (float): Die Verstärkungskonstante des P-Reglers.
            stop_distance (int): Die Distanz in cm, bei der das Auto anhalten soll.
        '''
        print(f"Fahrmodus 7: Linienverfolgung mit Hindernis-Stopp bei < {stop_distance} cm.")
        
        sensor_weights = np.array([-2, -1, 0, 1, 2])

        while True:
            # 1. Priorität: Hinderniserkennung
            distance = self.get_distance()
            if distance <= stop_distance:
                print(f"Hindernis bei {distance} cm erkannt. Stoppe.")
                self.stop()
                break

            # 2. Priorität: Linienverfolgung
            line_status = np.array(self.get_line_status())

            if np.sum(line_status) == 0:
                print("Linie verloren oder Ende erreicht. Stoppe.")
                self.stop()
                break
            
            error = np.sum(line_status * sensor_weights)
            correction = Kp * error
            steering_angle = 90 + correction
            
            self.drive(speed, steering_angle)
            
            time.sleep(0.01)
    # Patrick-Methode: ir-Grounding
    # Diese Methode setzt die Referenzwerte der Infrarotsensoren basierend auf
    # den durchschnittlichen Werten des Bodens, um eine bessere Linienverfolgung zu
    # ermöglichen. Sie sollte nur einmal zu Beginn der Nutzung aufgerufen werden.
    def reference_ground(self):
        sumlist= []
        start_zeit = time.time()
        print(self.__ir._references)
        while time.time() - start_zeit < 2:
            data = self.__ir.get_average()
            sumlist.append(round(np.sum(data),1))
        reference = round(np.mean(sumlist)/len(data)*0.8,1)
        print(reference)
        reference_list = []
        for i in range(len(data)): 
            reference_list.append(reference)
        self.__ir.set_references(reference_list)
        print(self.__ir._references)
        with open(SensorCar.HARDWARE_CONFIG_FILE, "r") as f:
            data = json.load(f)
        
        data["infrared_reference"] = reference_list
        with open(SensorCar.HARDWARE_CONFIG_FILE, "w") as f:
            json.dump(data, f, indent= 2)


if __name__ == '__main__':
    # Beispielhafte Verwendung der SensorCar-Klasse
    # WICHTIG: Stellen Sie sicher, dass das Auto genügend Platz hat!
    # Heben Sie das Auto zu Beginn an, um die Räder frei drehen zu lassen.
    
    car = SensorCar()
    #car.reference_ground()  # Optional: Referenzwerte der Infrarotsensoren setzen
    start_time = time.time()    
    try:
        print("Wählen Sie einen Fahrmodus:")
        print("5 - Einfache Linienverfolgung")
        print("6 - Erweiterte Linienverfolgung (60s)")
        print("7 - Linienverfolgung mit Hinderniserkennung")
        modus = input("Ihre Wahl: ")

        if modus == '5':
            input("Stellen Sie das Auto auf den Anfang der Linie. Drücken Sie Enter zum Starten...")
            car.line_follower(speed=40)
        
        elif modus == '6':
            input("Stellen Sie das Auto auf eine geschlossene Linie. Drücken Sie Enter zum Starten...")
            car.advanced_line_follower(speed=30, duration_s=60)
            
        elif modus == '7':
            input("Stellen Sie das Auto auf die Linie. Hindernis wird bei <15cm erkannt. Enter zum Starten...")
            car.line_follower_with_obstacle_avoidance(speed=25, stop_distance=15)
            
        else:
            print("Ungültige Auswahl.")

    except KeyboardInterrupt:
        print("\nProgramm durch Benutzer unterbrochen.")
    
    finally:
        print("Fahrt beendet. Setze Auto in sicheren Zustand.")
        car.stop()
        
        # Optional: Fahrtenbuch am Ende ausgeben oder speichern
        # import json
        # with open('fahrt_log.json', 'w') as f:
        #     json.dump(car.log, f, indent=4)
        # print("Fahrtenbuch wurde in 'fahrt_log.json' gespeichert.")
        