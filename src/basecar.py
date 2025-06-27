from basisklassen import FrontWheels, BackWheels
import time
import util.json_loader as loader

from threading import Event

class BaseCar:
    '''
    BaseCar Klasse ist die Klasse mit den Grundfahrfunktionen des Fahrzeuges.

    Methoden:
        drive - gibt Geschwindigkeit, Fahrrichtung (durch das Vorzeichen der Geschwindigkeit) und Lenkwinkel (Fahrmodus)
        stop - setzt speed zu 0
    
    Begrenzungswerte:
        Der Lenkwinkel ist nur im Wertebereich 45 bis 135 (90 ist geradeaus)
        Die Geschwindigkeit ist im Wertebereich -100 bis 100 (negative Geschwindigkeiten erzeugen eine Rückwärtsfahrt)
        
    '''
    #Definition von Konstanten(alles Groß geschrieben) mit nicht mehr veränderbaren Werten
    MAX_STEERING_ANGLE = 135
    MIN_STEERING_ANGLE = 45

    MAX_SPEED = 100
    MIN_SPEED = -100

    #Standardkonstruktor der Klasse, da alle Parmetern vordefinierten Werte haben.
    def __init__(self, steering_angle: int = 90, speed: int = 0, direction: int = 0):

        cfg = loader.readjson("src/config/car_hardware_config.json")

        self.__steering_angle = steering_angle
        self.__speed = speed
        self.__direction = direction  

        self.__fw = FrontWheels(cfg["turning_offset"]) 
        self.__bw = BackWheels(cfg["forward_A"], cfg["forward_B"])      

        # Initialisierung der Datenaufzeichnung
        self.log = []

        # Flag, ob ein Fahrprozess gerade läuft
        # wird von Fahrprozessen abgefragt, wird beim Start eines Fahrmodus True gesetzt
        self._running = False

        # fancy time.sleep
        # nutzt Event.wait, unterbrechung mit .set()
        self._stop_event = Event()

    #Property auf Privat-Attribut __steering_angle, Aufruf und Setzen erlaubt
    @property
    def steering_angle(self):
        return self.__steering_angle
    
    #Ermöglicht das Setzen von __steering_angle
    @steering_angle.setter
    def steering_angle(self, new_angle: int):
        self.__steering_angle = self.__checkSteeringAngle(new_angle)
    #Property auf Privat-Attribut __speed, Aufruf und Setzen erlaubt
    @property
    def speed(self):
        #print(f"get speed: {self.__speed}")
        return self.__speed
    
    @speed.setter
    def speed(self, speed: int):
        #print(f"set speed: {speed}")
        self.__speed = self.__checkSpeed(speed)
    
    @property
    def direction(self):
        return self.__direction
    
    def __checkSteeringAngle(self, angle: int) -> int:
        #Sicherstellen, dass der Winkel im Gültigkeitsbereich bleibt
        if angle < self.MIN_STEERING_ANGLE: 
            return self.MIN_STEERING_ANGLE 
        elif angle > self.MAX_STEERING_ANGLE:
            return self.MAX_STEERING_ANGLE
        return angle
    
    def __checkSpeed(self, speed: int) -> int:
        #Sicherstellen, dass die Geschwindigkeit im Gültigkeitsbereich bleibt
        if speed < self.MIN_SPEED:
            return self.MIN_SPEED
        elif speed > self.MAX_SPEED:
            return self.MAX_SPEED
        return speed
    
    def checkSteeringAngle(self, angle: int) -> int:
        return self.__checkSteeringAngle(angle)

    def checkSpeed(self, speed: int) -> int:
        return self.__checkSpeed(speed)
    
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
        }
        self.log.append(status_record)
        # Optional: Log-Ausgabe in der Konsole für Echtzeit-Debugging
        # print(status_record)

    
    def drive(self, speed: int = None, angle: int = None):
        '''
        Die drive-Methode setzt mittels Parameter speed die Geschwindigkeit und die Fahrtrichtung (über Vorzeichen) und 
        mittels Parameter angle wird der Lenkwinkel gesetzt.

        Parameter:
            speed - optional, wenn nicht angegeben wird der alte Wert übernommen und ist begrenzt auf den Wertebereich (-100 bis 100)
            angle - optional, wenn nicht angegeben wird der alte Wert übernommen und ist begrenzt auf den Wertebereich (45 Volleinschlag links | 90 geradeaus | 135 Volleinschlag rechts)

        Return - Value:
            gibt keinen Wert zurück

        '''
        # Initialisierung von Variablen gewährleisten
        if angle is not None:
            self.__steering_angle = angle
        if speed is not None:
            self.__speed = speed
        #__speed-Vorzeichen bestimmt die Fahrtrichtung, sonst einhalten
        if self.__speed > 0:
            self.__bw.forward()
            self.__direction = 1
        elif self.__speed < 0:
            self.__bw.backward()
            self.__direction = -1
        else:
            self.stop()
        #Drehung vornehmen
        self.__fw.turn(self.__steering_angle)
        #Speed wieder positiv festlegen, da nur 0 bis 100 erlaubt für __bw.speed
        self.__bw.speed = abs(self.__speed)        

    def stop(self):
        '''
        Die stop-Methode setzt die Geschwindigkeit auf 0 

        Parameter:
            keine Parameter

        Return-Value:
            gibt keinen Wert zurück

        '''
        #Fahrzeug wird eingehalten(__bw.speed auf 0)
        self.__bw.stop()
        #Klassen-Interne Richtung auf 0 setzen.
        self.__direction = 0

    def hard_stop(self):
        """ Unterbricht zusätzlich loops und timer
        """
        self.stop()
        self._stop_event.set()
        self._running = False

    def fahrmodus1(self, geschwindigkeit: int, fahrzeit: float):
        """fahrmodus1 

        Parameters
        ----------
        geschwindigkeit : int
            Fahrzeuggeschwindigkeit, ist über die Fahrzeit konstant
        fahrzeit : float
            Gesamtfahrzeit des Fahrzeugs
        """
        self._running = True
        self._stop_event.clear()

        self.drive(speed = geschwindigkeit, angle = 90)
        self._log_status()

        if self._stop_event.wait(timeout=fahrzeit/2):
            self.log.info(f"route manually terminated")
            self._running = False
            return
            
        self.drive(speed = geschwindigkeit *-1, angle = 90)
        self._log_status()

        if self._stop_event.wait(timeout=fahrzeit/2):
            self.log.info(f"route manually terminated")
            self._running = False
            return
        
        self.stop()
        self._log_status()

 
    def fahrmodus2(self, geschwindigkeit: int, lenkwinkel: int):
        """fahrmodus1 

        Parameters
        ----------
        geschwindigkeit : int
            Fahrzeuggeschwindigkeit, ist über die Fahrzeit konstant.
            Bei der Rückwärtsfahrt wird dieselbe Geschwindigkeit genutzt.
        lenkwinkel : float
            Lenkwinkel für die Kreisfahrt
        """
        self._running = True
        self._stop_event.clear()

        self.drive(speed = geschwindigkeit, angle = 90)
        self._log_status()
        
        if self._stop_event.wait(timeout=1):
            self.log.info(f"route manually terminated")
            self._running = False
            return

        self.drive(speed = geschwindigkeit, angle = lenkwinkel)
        self._log_status()
        
        if self._stop_event.wait(timeout=8):
            self.log.info(f"route manually terminated")
            self._running = False
            return

        self.drive(speed = geschwindigkeit *-1, angle = lenkwinkel)
        self._log_status()
        
        if self._stop_event.wait(timeout=8):
            self.log.info(f"route manually terminated")
            self._running = False
            return

        self.drive(speed = geschwindigkeit *-1, angle = 90)
        self._log_status()
        
        if self._stop_event.wait(timeout=1):
            self.log.info(f"route manually terminated")
            self._running = False
            return

        self.stop()
        self._log_status()
 


if __name__ == '__main__':
    car = BaseCar()
    #car.fahrmodus1(-30,5)
    #car.stop()
   