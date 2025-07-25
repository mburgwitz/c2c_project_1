from basecar import BaseCar
from basisklassen import Ultrasonic
import time
import random
from random import normalvariate, randrange

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
        #print("SonicCar wurde initialisiert.")

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

    def stop(self):
        """
        Stop the car and cease ultrasound sensor operation.

        Overrides BaseCar.stop() to also halt the ultrasonic sensor.

        Returns
        -------
        None
        """
        # Wichtig: Erst Geschwindigkeit im internen Zustand anpassen, dann stoppen
        super().stop()
        self.__us.stop()  # Ultraschallsensor stoppen, falls nötig

    def hard_stop(self):
        """
        Immediately stop all car motion and loops, and shut down the sensor.

        Extends BaseCar.hard_stop() by ensuring the ultrasonic sensor is stopped.

        Returns
        -------
        None
        """
        super().hard_stop()
        self.__us.stop()

    # --- Implementierung der geforderten Fahrmodi ---

    def drive_until_obstacle(self, speed: int = 30, stop_distance: int = 20):
        '''
        Fahrmodus 3: Fährt geradeaus, bis ein Hindernis unterschritten wird.
        
        Args:
            speed (int): Die Geschwindigkeit für die Vorwärtsfahrt (1-100).
            stop_distance (int): Die Distanz in cm, bei der das Auto anhalten soll.
        '''
        print(f"Fahrmodus 3: Fahre vorwärts bis Distanz < {stop_distance} cm.")
        
        self._running = True

        # Geradeaus fahren starten
        self.drive(speed, 90)
        log_freq = 0.25  # Log-Frequenz in Sekunden
        last_log_time = 0
        while self._running:
            dist = self.get_distance()

            # Loggen, um die Distanzänderung zu sehen
            # act_time = time.time()
            # if act_time - last_log_time >= log_freq:
            #     last_log_time = act_time
            #     # Protokolliere den aktuellen Status  
            #     self._log_status()
            
            #self._log_status()
            
            if dist <= stop_distance:
                print(f"Hindernis bei {dist} cm erkannt. Stoppe.")
                self.stop()
                break
            
            time.sleep(0.25) # Kurze Pause, um CPU-Last zu reduzieren

    def explore(self, speed: int = 30, stop_distance: int = 25, duration_s: int = 30):
        '''
        Fahrmodus 4: Fährt für eine bestimmte Dauer autonom und weicht Hindernissen aus.

        Args:
            speed (int): Die Standard-Fahrgeschwindigkeit.
            stop_distance (int): Die Distanz, bei der ein Ausweichmanöver eingeleitet wird.
            duration_s (int): Die Gesamtdauer der Erkundungstour in Sekunden.
        '''
        print(f"Fahrmodus 4: Starte Erkundungstour für {duration_s} Sekunden.")
        start_time = time.time()

        self._running = True
        self._stop_event.clear()

        while (time.time() - start_time < duration_s) and self._running:
            print("Suche freien Weg...")
            # Starte die Vorwärtsfahrt
            self.drive(speed, 90)

            # Fahre vorwärts, solange der Weg frei ist
            while self.get_distance() > stop_distance:
                if (time.time() - start_time > duration_s) and self._running: break # Zeitlimit prüfen
                time.sleep(0.05)
            
            if not ((time.time() - start_time < duration_s) and self._running): break # Zeitlimit nach innerer Schleife prüfen

            print("Hindernis erkannt! Starte Ausweichmanöver.")
            self.stop()
            if self._stop_event.wait(timeout=0.5):
                print(f"route manually terminated")
                self._running = False
                return

            # Ausweichmanöver: zurücksetzen, drehen, anhalten
            print("1. Zurücksetzen")
            self.drive(-speed, 90) # Rückwärts gerade
            
            if self._stop_event.wait(timeout=1):
                print(f"route manually terminated")
                self._running = False
                return
                
            self.stop()
            if self._stop_event.wait(timeout=0.5):
                print(f"route manually terminated")
                self._running = False
                return

            print("2. Drehen")
            # Zufällig nach links oder rechts drehen
            turn_angle = random.choice([self.MIN_STEERING_ANGLE, self.MAX_STEERING_ANGLE])
            self.drive(speed, turn_angle) # 0 Räder im Stand drehen-> aus erfahrung bewege ich mich doch
            if self._stop_event.wait(timeout=1):
                print(f"route manually terminated")
                self._running = False
                return
            
            # Räder wieder gerade stellen, um für die nächste Runde bereit zu sein
            self.drive(speed, 90)
            if self._stop_event.wait(timeout=0.5):
                print(f"route manually terminated")
                self._running = False
                return

        print("Erkundungstour beendet.")
        self.stop()

    def random_drive(self, stop_at_obstacle: bool = True, stop_distance: int = 25,
                     normal_speed: int = 30, drive_time: int =20,
                     min_speed: int = 30, max_speed: int = 60):
        """
        Drive in random segments, adjusting speed and angle, optionally stopping or evading obstacles.

        The car selects random steering and speed variations around a base value, drives for
        short random intervals, and either stops or performs an evade maneuver upon detecting
        an obstacle within `stop_distance`. Continues until `drive_time` has elapsed or stopped.

        Parameters
        ----------
        stop_at_obstacle : bool, optional
            If True, stop when an obstacle is detected; if False, perform `evade_obstacle()`.
        stop_distance : int, optional
            Distance in cm at which to trigger stopping or evasion.
        normal_speed : int, optional
            Base speed around which random variation is applied.
        drive_time : int, optional
            Total duration in seconds for the random drive session.
        min_speed : int, optional
            Minimum allowable speed after variation.
        max_speed : int, optional
            Maximum allowable speed after variation.

        Returns
        -------
        None
        """

        try:

            start_exploration_time = time.time()

            self._running = True
            while(self._running):
                start_time = time.time()

                #self.speed = normal_speed

                delta_angle = round(normalvariate(0,20))
                tmp_angle = self.checkSteeringAngle(self.steering_angle + delta_angle)

                #delta_speed = randrange(-10,10,5)
                delta_speed = round(normalvariate(0,10))
                tmp_speed = self.speed + delta_speed

                if tmp_speed < min_speed:
                    tmp_speed = min_speed 
                elif tmp_speed > max_speed:
                    tmp_speed = max_speed 
                
                time_for_section = randrange(1,3)

                self.drive(speed=self.checkSpeed(tmp_speed), angle = tmp_angle)
                
                t_delta = time.time() - start_time

                while (t_delta < time_for_section) and self._running:
                    time.sleep(0.25)
                    t_delta = time.time() - start_time

                    distance = self.get_distance()

                    #self._log_status()

                    if distance < stop_distance:
                        if stop_at_obstacle:
                            self.stop()
                            self._running = False
                            break
                        else:
                            self.evade_obstacle()
                
                if time.time() - start_exploration_time > drive_time:
                    self._running = False
                    print(f"drive time limit of {drive_time} seconds reached")

        except Exception as e:
            print(f"{e}")
        finally:
            self.stop()

    def evade_obstacle(self) -> None:
        """
        Execute an obstacle evasion maneuver by reversing and turning, then restore state.

        Saves the current speed and steering angle, performs a backward turn at a fixed
        speed and angle for a short duration, then resets speed and heading to prior values.

        Returns
        -------
        None
        """
        prev_speed = self.speed
        prev_angle = self.steering_angle

        tmp_angle = self.steering_angle
        if tmp_angle > 90:
            tmp_angle = self.MIN_STEERING_ANGLE
        else:
            tmp_angle = self.MAX_STEERING_ANGLE

        tmp_speed = -30
        tmp_time = 2

        self.drive(speed=tmp_speed, angle= tmp_angle)

        start_time = time.time()
        t_delta = time.time() - start_time

        self._running = True
        while (t_delta < tmp_time) and self._running:
            time.sleep(0.25)
            t_delta = time.time() - start_time

            distance = self.get_distance()

        self.speed = prev_speed 
        self.steering_angle = prev_angle 

if __name__ == "__main__":

    car = SonicCar()