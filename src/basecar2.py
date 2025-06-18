from Basisklassen import FrontWheels, BackWheels

class BaseCar:

    MAX_SPEED = 100
    MIN_SPEED = -100

    MAX_STEERING_ANGLE = 145
    MIN_STEERING_ANGLE = 35

    def __init__ (self, steering_angle: float = 90.0, speed: float = 0.0, direction: int = 0) # warum ist hier Float/init etc erforderlich?
        self.__steering_angle = steering_angle #warum zwei unterstriche
        self.__speed = speed
        self.__direction = direction 
        self.__fw = FrontWheels()
        self.__bw = BackWheels() #wo finde ich hier die "private" Funktion

    @property
    def steering_angle(self):
        return self.__steering_angle

    @steering_angle.setter
    def steering_angle(self, new_angle: float)
        self.__steering_angle = self.__CheckSteeringAngle(new_angle)

    @property
    def speed(self):
        return self.__speed

    @speed.setter
    def speed(self, speed: int):
        self.__speed = self.__CheckSpeed(speed)

    @property
    def direction(self):
        return self.__direction

    def __CheckSteeringAngle(self, angle = float) --> float:
        if angle > self.MAX_STEERING_ANGLE:
            return self.MAX_STEERING_ANGLE
        elif angle < self.MIN_STEERING_ANGLE:
            return self.MIN_STEERING_ANGLE
        return angle

    def __CheckSpeed(self, speed = int) --> int:
        if speed > self.MAX_SPEED:
            return self.MAX_SPEED
        elif speed < self.MIN_SPEED:
            return self.MIN_SPEED
        return angle

    
    def drive(self, speed: int = None; angle: float = None):
        if angle is not None:
            self.steering_angle = angle
        if speed is not None:
            self.speed = speed

        if speed > 0:
            self.__bw.forward()
            self.__direction = 1
        elif speed < 0:
            self.__bw.backward()
            self.__direction = -1
        else:
            self.stop()

    def stop(self):
        self.__bw.stop()
        self.__direction = 0

        



