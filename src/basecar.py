from basisklassen import FrontWheels, BackWheels # Man könnte auch alles importieren, aber in diesem Fall sind nur Front/BackWheels erforderlich, dann wird der gesamte Code ausgeführt

class BaseCar:

    MAX_STEERING_ANGLE = 135
    MIN_STEERING_ANGLE = 45

    MAX_SPEED = 100
    MIN_SPEED = -100

    def __init__(self, steering_angle: float = 90.0, speed: float = 0.0, direction: int = 0):
    # Self als eigene Instanz innerhalb der Klasse BaseCar (Privat)
        self.__steering_angle = steering_angle
        self.__speed = speed
        self.__direction = direction  
        self.__fw = FrontWheels()
        self.__bw = BackWheels()      

    @property
    def steering_angle(self):
        return self.__steering_angle
    
    @steering_angle.setter
    def steering_angle(self, new_angle: float):
        self.__steering_angle = self.__checkSteeringAngle(new_angle)
    
    @property
    def speed(self):
        return self.__speed
    
    @speed.setter
    def speed(self, speed: int):
        self.__speed = self.__checkSpeed(speed)
    
    @property
    def direction(self):
        return self.__direction
    
    def __checkSteeringAngle(self, angle: float) -> float:
        if angle < self.MIN_STEERING_ANGLE: 
            return self.MIN_STEERING_ANGLE 
        elif angle > self.MAX_STEERING_ANGLE:
            return self.MAX_STEERING_ANGLE
        return angle
    
    def __checkSpeed(self, speed: int) -> int:
        if speed < self.MIN_SPEED:
            return self.MIN_SPEED
        elif speed > self.MAX_SPEED:
            return self.MAX_SPEED
        return speed
    
    def drive(self, speed: int = None, angle: float = None):
        if angle is not None:
            self.steering_angle = angle
        if speed is not None:
            self.speed = speed

        if self.speed > 0:
            self.__bw.forward()
            self.__direction = 1
        elif self.speed < 0:
            self.__bw.backward()
            self.__direction = -1
        else:
            self.stop()

        self.__fw.turn(self.steering_angle)
        self.__bw.speed = abs(self.speed)        

    def stop(self):
        self.__bw.stop()
        self.__direction = 0



if __name__ == '__main__':
    car = BaseCar()

    import time

    # Fahrmodus 1
    car.drive(speed = 30)
    time.sleep(3)
    
    car.stop()
    time.sleep(1)

    car.drive(speed = -30)
    time.sleep(3)

    car.stop()


    time.sleep(3)

    # Fahrmodus 2
    car.drive(speed = 30, angle= 90)
    time.sleep(1)
    
    car.drive(speed = 30, angle = 135)
    time.sleep(8)

    car.drive(speed= -30, angle = 135)
    time.sleep(8)

    car.drive(speed = -30, angle= 90)
    time.sleep(1)

    car.stop()
    
