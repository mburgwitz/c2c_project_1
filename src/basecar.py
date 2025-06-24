from basisklassen import FrontWheels, BackWheels
from util.logger import Logger
from util.config.manager import ConfigManager
import time
from datetime import datetime
import pandas as pd

from threading import Event

class BaseCar:
    """ Provides basic driving functionality.

    Attributes
    ----------
    MAX_STEERING_ANGLE : int
        Maximum steering angle in degrees.
    MIN_STEERING_ANGLE : int
        Minimum steering angle in degrees.
    MAX_SPEED : int
        Maximum forward speed.
    MIN_SPEED : int
        Minimum reverse speed (negative value).
    """

    # Kontanten, vorgegeben durch das Lastenheft
    MAX_STEERING_ANGLE = 135
    MIN_STEERING_ANGLE = 45

    MAX_SPEED = 100
    MIN_SPEED = -100

    # Standardkonstruktor der Klasse
    def __init__(self, cfg_name: str = 'car_initial_values.json'):

        # set up logging
        self.log = Logger.get_logger("BaseCar") 
        self.log.debug('initialize BaseCar')
        
        # load config
        self.log.debug('load config')
        ConfigManager.load('./config', cfg_name, name = cfg_name)

        # set initial values based on config
        self.__steering_angle = ConfigManager.get('steering_angle',name=cfg_name)
        self.__speed = ConfigManager.get('speed',name=cfg_name)
        self.__direction = 1 if self.__speed > 0 else (-1 if self.__speed < 0 else 0)

        self.log.debug(f'imported steering_angle: {self.__steering_angle}, speed: {self.__speed} and got direction {self.__direction}')

        self.__fw = FrontWheels()
        self.__bw = BackWheels()             

        self.drive_log = {}

        self._running = False
        self._stop_event = Event()

        self.log.info("init finished")

    #------------------------------------
    # properties
    #------------------------------------

    # Definition der property für __steering_angle (getter)
    @property
    def steering_angle(self):
        """
        Get the current steering angle of the car.

        Returns
        -------
        steering angle : int
            The current steering angle
        """
        return self.__steering_angle
    
    # Definition des setter für __steering_angle
    @steering_angle.setter
    def steering_angle(self, new_angle: int):
        """
        Set the steering angle and clamp it within bounds.

        Parameters
        ----------
        new_angle : int
            The new steering angle in degrees.
        """
        self.__steering_angle = self.check_steering_angle(new_angle)
    
    # Definition der property für __speed (getter)
    @property
    def speed(self):
        """
        Get the current speed of the car.

        Returns
        -------
        speed : int
            The current speed
        """
        return self.__speed
    
    # Definition des setter für __speed
    @speed.setter
    def speed(self, new_speed: int):
        """
        Set the speed and clamp it within bounds.

        Parameters
        ----------
        new_speed : int
            The new car speed.
        """
        self.__speed = self.check_speed(new_speed)
    
    # Definition der property für __direction (getter)
    @property
    def direction(self):
        """
        Get the direction of the car.

        Returns
        -------
        int
            The current direction:
            -1 for reverse,
            0 for stationary,
            1 for forward.
        """
        return self.__direction
    
    #------------------------------------
    # private methods
    #------------------------------------
    
    def check_steering_angle(self, angle: int) -> int:
        """
        Clamp the angle to the valid steering range.

        Parameters
        ----------
        angle : int
            The requested steering angle.

        Returns
        -------
        angle : int
            A valid angle within [MIN_STEERING_ANGLE, MAX_STEERING_ANGLE].
        """

        # Sicherstellen, dass der Winkel im gültigen Bereich ist
        if angle < self.MIN_STEERING_ANGLE: 
            return self.MIN_STEERING_ANGLE 
        elif angle > self.MAX_STEERING_ANGLE:
            return self.MAX_STEERING_ANGLE
        return angle
    
    def check_speed(self, speed: int) -> int:
        """
        Clamp the speed to the valid speed range.

        Parameters
        ----------
        speed : int
            The requested speed value.

        Returns
        -------
        speed : int
            A valid speed within [MIN_SPEED, MAX_SPEED].
        """

        # Sicherstellen, dass die Geschwindigkeit im gültigen Bereich ist
        if speed < self.MIN_SPEED:
            return self.MIN_SPEED
        elif speed > self.MAX_SPEED:
            return self.MAX_SPEED
        return speed
    
    #------------------------------------
    # public methods
    #------------------------------------
    
    def drive(self, speed: int = None, angle: int = None):
        """
        Control the driving speed and steering angle of the car.

        Parameters
        ----------
        speed : int, optional
            The new speed of the car. If None, the previous speed is retained.
            Positive values drive forward, negative values drive backward.
        angle : int, optional
            The new steering angle of the car. If None, the previous angle is retained

        Notes
        -----
        The direction is updated based on the speed:
        - speed > 0 → forward (direction = 1)
        - speed < 0 → backward (direction = -1)
        - speed == 0 → stop (direction = 0)
        """

        self.log.debug(f"start drive")

        try:
            # Prüfen, ob Winkel neu gesetzt wurde
            if angle is not None:
                self.steering_angle = angle

            # Prüfen, ob Geschwindigkeit neu gesetzt wurde
            if speed is not None:
                self.speed = speed

            # Fahrtrichtung durch das Vorzeichen von speed bestimmen
            if self.speed > 0:
                self.__bw.forward()
                self.__direction = 1
            elif self.speed < 0:
                self.__bw.backward()
                self.__direction = -1
            else:
                self.stop()

            self.log.debug(f"speed: {self.speed}, angle: {self.steering_angle}, direction: {self.direction}")

            # Ansteuern der Lenkung / setzen des Lenkwinkels
            self.__fw.turn(self.steering_angle)

            # Geschwindigkeit setzen. Absolutwert nutzen, da nur Werte >= 0 akzeptiert werden
            self.__bw.speed = abs(self.speed)        
        except Exception as e:
            self.log.error(f"{e}")
            self.stop()

    def stop(self):
        """
        Stop the car.

        Notes
        -----
        Sets the speed and direction to zero (stationary). The steering angle
        remains unchanged.
        """
        
        # Anhalten des Fahrzeugs, speed wird auf 0 gesetzt
        self.__bw.stop()

        # Setzen der Fahrtichtung auf 0 (stationary)
        self.__direction = 0

        self.log.info("car stopped")

    def hard_stop(self):
        self.stop()
        self.log.info("...hard")
        self._stop_event.set()
        self._running = False
        

    def drive_fixed_route(self, 
                       schedule: str, 
                       base_path: str = 'config', 
                       filename: str = 'fahrplan.json',
                       log_tour: bool = True):


        ConfigManager.load(base_path = base_path,
                           filenames = filename,
                           name = "fahrplan"
                           )
        
        self.log.debug(f"loading schedule {schedule}")
        mode = ConfigManager.get(schedule, name = "fahrplan")
        self.log.debug(f"schedule {schedule} loaded: {mode}")

        self._running = True
        # iterate through every line in the schedule
        # Format: [mode, int | null, int | null, int | float]
        #   JSON null is automatically converted to None
        #   modes: 
        #       'd' for 'drive. ['d', speed, angle, time]
        #       's' for 'stop.  ['s', time]
        try:
            for idx, cmd in enumerate(mode['schedule']):
                self.log.debug(f"iterate cmd[{idx}]: {cmd}")
                md = str.lower(cmd[0])
                
                t = cmd[-1]

                # initialize log at start of the tour
                if log_tour and idx == 0:
                    self.new_log_entry(schedule)

                # type check and value check
                if not isinstance(t,(int, float)) and t > 0.0:
                    raise ValueError(f'Wrong type or value for time: \
                                        {t} type({type(t)}). \
                                        Expected value > 0 and type "int" or "float".') 

                if md == 'd':                   
                    speed = cmd[1]; angle = cmd[2]
                    
                    # type check
                    if  all(isinstance(x, int) or x is None for x in (speed, angle)):
                        self.log.debug(f"driving with speed {speed} and angle {angle} for {t} seconds")

                        self.drive(speed, angle)

                    else:
                        raise ValueError(f'Wrong type for speed and/or angle: \
                                        speed type({type(speed)}), angle type({type(angle)}). \
                                        Expected "int" or "None".')    
                elif md == 's':
                        self.log.debug(f"stopping for {t} seconds")
                        self.stop()
                        
                else:
                    raise ValueError(f'Wrong value for mode. Got {md}, expected "d" or "s".')
                
                # add log entry to log after all values are set
                if log_tour:                    
                    data = {"speed" : self.speed, 
                            "angle" : self.steering_angle, 
                            "direction" : self.direction }
                    self.add_log_to_entry(schedule, data)

                # exectute previously set task for t seconds
                if self._stop_event.wait(timeout=t):
                    self.log.info(f"route manually terminated")
                    self._running = False
                    self._stop_event.clear()
                    break
                
            
        except Exception as e:
            self.log.error(f"{ e }")

        finally:
            self.stop()

    def get_log_columns(self):
        return ["speed", "direction", "angle", "timestamp"]

    def new_log_entry(self, entry_name: str):
        cols = self.get_log_columns()
        self.log.debug(f"new log '{entry_name}' with cols {cols} type({type(cols)})")
        self.drive_log[entry_name] = pd.DataFrame(columns=cols)
        self.log.debug(f"initialized log {entry_name}")
    
    def add_log_to_entry(self, entry_name: str, data: dict):
        if entry_name not in self.drive_log.keys():
            raise ValueError(f"No Log with name {entry_name}")
        
        if 'timestamp' not in data.keys():
            data['timestamp'] = datetime.now().strftime('%Y.%m.%d %H:%M:%S')

        # fetch columns defined in get_log_columns() and get corresponding entry from data
        # assign None if column is not found
        row = {col: data.get(col, None) for col in self.get_log_columns()}

        self.log.info(f"logging data: {data}")

        self.drive_log[entry_name].loc[len(self.drive_log[entry_name])] = row
        self.log.debug(f"added {row} to log {entry_name}")
        


if __name__ == '__main__': 

    car = BaseCar() 
    car.drive_fixed_route("fahrmodus_1")

    car.log.debug(f"complete log:  {car.drive_log}")