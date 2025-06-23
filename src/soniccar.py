from basecar import BaseCar
from basisklassen import Ultrasonic
import time
import random

class SonicCar(BaseCar):
    '''
    Die SonicCar-Klasse erweitert die BaseCar-Klasse um die Funktionalität eines Ultraschallsensors.
    Sie kann Hindernisse erkennen und darauf reagieren sowie ihre Fahrdaten aufzeichnen.

    Erbt von:
        BaseCar

    Neue Methoden:
        get_distance() - Gibt die aktuelle Distanz zum nächsten Hindernis in cm zurück.
        drive_until_obstacle(speed, stop_distance) - Fährt vorwärts, bis ein Hindernis erkannt wird.
        explore(speed, stop_distance) - Fährt autonom und weicht Hindernissen aus.
    
    Datenaufzeichnung:
        Die Eigenschaft 'log' enthält eine Liste von Dictionaries mit den aufgezeichneten Fahrdaten.
    '''

    def __init__(self, steering_angle: int = 90, speed: int = 0):
        '''
        Konstruktor für die SonicCar-Klasse.

        Initialisiert die übergeordnete BaseCar-Klasse, den Ultraschallsensor
        und die Datenaufzeichnungsliste.
        '''
        # Initialisierung der Basisklasse
        super().__init__(steering_angle, speed)

        # Instanziierung des Ultraschallsensors
        self.__us = Ultrasonic()
        
        
        
        print("SonicCar wurde initialisiert.")

    def get_distance(self) -> int:
        '''
        Fragt den Ultraschallsensor ab und gibt die Distanz in cm zurück.
        Fehlerwerte des Sensors (<0) werden als sehr große Distanz (999) interpretiert,
        um die Logik in den Fahrmodi zu vereinfachen.

        Returns:
            int: Gemessene Distanz in cm oder 999 bei einem Sensorfehler.
        '''
        distance = self.__us.distance()
        if distance < 0:
            return 999  # Fehlerwert als "freie Fahrt" interpretieren
        return distance

    def _log_status(self):
        '''
        Private Methode, um den aktuellen Status des Fahrzeugs zu protokollieren.
        Wird von den überschriebenen Methoden drive() und stop() aufgerufen.
        '''
        '''Diese Daten beschreiben den Status des Autos
        (Geschwindigkeit, Fahrtrichtung, Lenkwinkel) und die Daten des Ultraschallsensors.
        Die Aufzeichnung/Speicherung der Daten soll für jede Steueranwesiung geschehen und
        somit die Fahr bzw. deren Steuerung protokolieren.'''
        status_record = {
            "timestamp": time.time(),
            "speed": self.speed,
            "steering_angle": self.steering_angle,
            "direction": self.direction,
            "distance_cm": self.get_distance()
        }
        self.log.append(status_record)
        # Optional: Log-Ausgabe in der Konsole für Echtzeit-Debugging
        # print(status_record)

    def drive(self, speed: int = None, angle: int = None):
        '''
        Überschreibt die drive-Methode von BaseCar, um die Datenaufzeichnung hinzuzufügen.
        '''
        super().drive(speed, angle)
        self._log_status()

    def stop(self):
        '''
        Überschreibt die stop-Methode von BaseCar, um die Datenaufzeichnung hinzuzufügen.
        '''
        # Wichtig: Erst Geschwindigkeit im internen Zustand anpassen, dann stoppen
        super().stop()
        self.__us.stop()  # Ultraschallsensor stoppen, falls nötig
        self._log_status()

    # --- Implementierung der geforderten Fahrmodi ---

    def drive_until_obstacle(self, speed: int = 30, stop_distance: int = 20):
        '''
        Fahrmodus 3: Fährt geradeaus, bis ein Hindernis unterschritten wird.
        
        Args:
            speed (int): Die Geschwindigkeit für die Vorwärtsfahrt (1-100).
            stop_distance (int): Die Distanz in cm, bei der das Auto anhalten soll.
        '''
        print(f"Fahrmodus 3: Fahre vorwärts bis Distanz < {stop_distance} cm.")
        
        # Geradeaus fahren starten
        self.drive(speed, 90)
        log_freq = 0.25  # Log-Frequenz in Sekunden
        last_log_time = 0
        while True:
            dist = self.get_distance()

            # Loggen, um die Distanzänderung zu sehen
            act_time = time.time()
            if act_time - last_log_time >= log_freq:
                last_log_time = act_time
                # Protokolliere den aktuellen Status  
                self._log_status()
            
            #self._log_status()
            
            if dist <= stop_distance:
                print(f"Hindernis bei {dist} cm erkannt. Stoppe.")
                self.stop()
                break
            
            time.sleep(0.25) # Kurze Pause, um CPU-Last zu reduzieren

    def explore(self, speed: int = 30, stop_distance: int = 25, duration_s: int = 60):
        '''
        Fahrmodus 4: Fährt für eine bestimmte Dauer autonom und weicht Hindernissen aus.

        Args:
            speed (int): Die Standard-Fahrgeschwindigkeit.
            stop_distance (int): Die Distanz, bei der ein Ausweichmanöver eingeleitet wird.
            duration_s (int): Die Gesamtdauer der Erkundungstour in Sekunden.
        '''
        print(f"Fahrmodus 4: Starte Erkundungstour für {duration_s} Sekunden.")
        start_time = time.time()

        while time.time() - start_time < duration_s:
            print("Suche freien Weg...")
            # Starte die Vorwärtsfahrt
            self.drive(speed, 90)

            # Fahre vorwärts, solange der Weg frei ist
            while self.get_distance() > stop_distance:
                if time.time() - start_time > duration_s: break # Zeitlimit prüfen
                time.sleep(0.05)
            
            if not (time.time() - start_time < duration_s): break # Zeitlimit nach innerer Schleife prüfen

            print("Hindernis erkannt! Starte Ausweichmanöver.")
            self.stop()
            time.sleep(0.5)

            # Ausweichmanöver: zurücksetzen, drehen, anhalten
            print("1. Zurücksetzen")
            self.drive(-speed, 90) # Rückwärts gerade
            time.sleep(2)
            self.stop()
            time.sleep(0.5)

            print("2. Drehen")
            # Zufällig nach links oder rechts drehen
            turn_angle = random.choice([self.MIN_STEERING_ANGLE, self.MAX_STEERING_ANGLE])
            self.drive(speed, turn_angle) # 0 Räder im Stand drehen-> aus erfahrung bewege ich mich doch
            time.sleep(1)
            
            # Räder wieder gerade stellen, um für die nächste Runde bereit zu sein
            self.drive(speed, 90)
            time.sleep(0.5)

        print("Erkundungstour beendet.")
        self.stop()

if __name__ == "__main__":

    car = SonicCar()