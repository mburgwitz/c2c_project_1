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
    def __init__(self, steering_angle: int = 90.0, speed: int = 0.0, direction: int = 0):
        """
        Initialize BaseCar with steering angle, speed, and direction, and set up hardware and logging.

        Parameters
        ----------
        steering_angle : int, optional
            Initial steering angle (default is 90, straight ahead).
        speed : int, optional
            Initial speed (default is 0).
        direction : int, optional
            Initial direction flag: 1 for forward, -1 for reverse, 0 for stopped.
        """
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
        """
        Get the current steering angle, constrained to [MIN_STEERING_ANGLE, MAX_STEERING_ANGLE].

        Returns
        -------
        int
            The current steering angle in degrees.
        """
        return self.__steering_angle
    
    #Ermöglicht das Setzen von __steering_angle
    @steering_angle.setter
    def steering_angle(self, new_angle: int):
        """
        Set the steering angle to a new value within allowed bounds.

        Parameters
        ----------
        new_angle : int
            Desired steering angle; will be clipped to [MIN_STEERING_ANGLE, MAX_STEERING_ANGLE].
        """
        self.__steering_angle = self.__checkSteeringAngle(new_angle)

    #Property auf Privat-Attribut __speed, Aufruf und Setzen erlaubt
    @property
    def speed(self):
        """
        Get the current vehicle speed, constrained to [MIN_SPEED, MAX_SPEED].

        Returns
        -------
        int
            The current speed; sign indicates direction.
        """
        return self.__speed
    
    @speed.setter
    def speed(self, speed: int):
        """
        Set the vehicle speed to a new value within allowed bounds.

        Parameters
        ----------
        speed : int
            Desired speed; will be clipped to [MIN_SPEED, MAX_SPEED].
        """
        self.__speed = self.__checkSpeed(speed)
    
    @property
    def direction(self):
        """
        Get the current travel direction based on speed sign.

        Returns
        -------
        int
            1 if moving forward, -1 if moving backward, 0 if stopped.
        """
        return self.__direction
    
    def __checkSteeringAngle(self, angle: int) -> int:
        """
        Constrain an input steering angle to the valid range.

        Parameters
        ----------
        angle : int
            Proposed steering angle.

        Returns
        -------
        int
            Steering angle clipped to [MIN_STEERING_ANGLE, MAX_STEERING_ANGLE].
        """
        #Sicherstellen, dass der Winkel im Gültigkeitsbereich bleibt
        if angle < self.MIN_STEERING_ANGLE: 
            return self.MIN_STEERING_ANGLE 
        elif angle > self.MAX_STEERING_ANGLE:
            return self.MAX_STEERING_ANGLE
        return angle
    
    def __checkSpeed(self, speed: int) -> int:
        """
        Constrain an input speed to the valid range.

        Parameters
        ----------
        speed : int
            Proposed speed.

        Returns
        -------
        int
            Speed clipped to [MIN_SPEED, MAX_SPEED].
        """
        #Sicherstellen, dass die Geschwindigkeit im Gültigkeitsbereich bleibt
        if speed < self.MIN_SPEED:
            return self.MIN_SPEED
        elif speed > self.MAX_SPEED:
            return self.MAX_SPEED
        return speed
    
    def checkSteeringAngle(self, angle: int) -> int:
        """
        Public wrapper to validate a steering angle without setting it.

        Parameters
        ----------
        angle : int
            Steering angle to check.

        Returns
        -------
        int
            Clipped steering angle within valid bounds.
        """
        return self.__checkSteeringAngle(angle)

    def checkSpeed(self, speed: int) -> int:
        """
        Public wrapper to validate a speed value without setting it.

        Parameters
        ----------
        speed : int
            Speed value to check.

        Returns
        -------
        int
            Clipped speed within valid bounds.
        """
        return self.__checkSpeed(speed)
    
    def _log_status(self):
        """
        Record the current timestamp, speed, and steering angle to the log.

        Appends a status dictionary to `self.log` for later analysis.
        """

        status_record = {
            "timestamp": time.time(),
            "speed": self.speed,
            "steering_angle": self.steering_angle
        }
        self.log.append(status_record)
    
    def drive(self, speed: int = None, angle: int = None):
        """
        Command the vehicle to drive at a given speed and steering angle, logging before and after.

        Parameters
        ----------
        speed : int, optional
            Desired speed; if None, retains current speed.
        angle : int, optional
            Desired steering angle; if None, retains current angle.
        """

        self._log_status()   
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
            self.__bw.stop()
        #Drehung vornehmen
        self.__fw.turn(self.__steering_angle)
        #Speed wieder positiv festlegen, da nur 0 bis 100 erlaubt für __bw.speed
        self.__bw.speed = abs(self.__speed)   
        self._log_status()     

    def stop(self):
        """
        Stop the vehicle by setting speed to zero via the drive method.

        This will also update the log accordingly.
        """
        self.drive(speed = 0)

    def hard_stop(self):
        """
        Immediately halt all motion and running loops.

        Sets speed to zero, raises the stop event, and marks the car as not running.
        """

        self.stop()
        self._stop_event.set()
        self._running = False

    def fahrmodus1(self, geschwindigkeit: int, fahrzeit: float):
        """
        Execute drive mode 1: forward then reverse for equal halves of the given time.

        Parameters
        ----------
        geschwindigkeit : int
            Speed to use in both forward and reverse segments.
        fahrzeit : float
            Total duration of the mode in seconds.
        """
        self._running = True
        self._stop_event.clear()

        self.drive(speed = geschwindigkeit, angle = 90)

        if self._stop_event.wait(timeout=fahrzeit/2):
            self._running = False
            return
            
        self.drive(speed = geschwindigkeit *-1, angle = 90)
        if self._stop_event.wait(timeout=fahrzeit/2):
            self._running = False
            return

        self.stop()

 
    def fahrmodus2(self, geschwindigkeit: int, lenkwinkel: int):
        """
        Execute drive mode 2: perform a circular path, reverse circle, and return straight.

        Parameters
        ----------
        geschwindigkeit : int
            Speed to use throughout the maneuver.
        lenkwinkel : int
            Steering angle to produce the circular path.
        """
        self._running = True
        self._stop_event.clear()

        self.drive(speed = geschwindigkeit, angle = 90)
        
        if self._stop_event.wait(timeout=1):
            self._running = False
            return

        self.drive(speed = geschwindigkeit, angle = lenkwinkel)
        
        if self._stop_event.wait(timeout=8):
            self._running = False
            return

        self.drive(speed = geschwindigkeit *-1, angle = lenkwinkel)
        
        if self._stop_event.wait(timeout=8):
            self._running = False
            return

        self.drive(speed = geschwindigkeit *-1, angle = 90)

        if self._stop_event.wait(timeout=1):
            self._running = False
            return
        
        self.stop() 
