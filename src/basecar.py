from basisklassen import FrontWheels, BackWheels

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
    def __init__(self, steering_angle: int = 90.0, speed: int = 0.0, direction: int = 0):
        self.__steering_angle = steering_angle
        self.__speed = speed
        self.__direction = direction  
        self.__fw = FrontWheels()
        self.__bw = BackWheels()      

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
        self.__steering_angle = self.__checkSteeringAngle(new_angle)
    
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
        self.__speed = self.__checkSpeed(new_speed)
    
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
    
    def __checkSteeringAngle(self, angle: int) -> int:
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
    
    def __checkSpeed(self, speed: int) -> int:
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

        # Prüfen, ob Winkel neu gesetzt wurde
        if angle is not None:
            self.steering_angle = angle

        # Prüfen, ob Geschwindigkeit neu gesetzt wurde
        if speed is not None:
            self.speed = speed

        # Fahrtrichtung durch das Vorzeichen von speed bestimmen
        if self.speed > 0:
            self.__bw.forward()
            self.direction = 1
        elif self.speed < 0:
            self.__bw.backward()
            self.direction = -1
        else:
            self.stop()

        # Ansteuern der Lenkung / setzen des Lenkwinkels
        self.__fw.turn(self.steering_angle)

        # Geschwindigkeit setzen. Absolutwert nutzen, da nur Werte >= 0 akzeptiert werden
        self.__bw.speed = abs(self.speed)        

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


if __name__ == '__main__':
    car = BaseCar()

    import time

    # Fahrmodus 1
    car.drive(speed = 30)
    time.sleep(3)
    
    car.stop()
    time.sleep(1)

    car.drive(speed = 30)
    time.sleep(3)

    car.stop()


    time.sleep(3)
    # Fahrmodus 2
    car.drive(speed = 30, angle= 90)
    time.sleep(1)
    
    car.drive(angle = 135)
    time.sleep(8)

    car.drive(speed=-30)
    time.sleep(8)

    car.drive(angle= 90)
    time.sleep(1)

    car.stop()
    
