from basisklassen import FrontWheels, BackWheels
from typing import Optional


class BaseCar:

    def __init__(self, steering_angle: float, speed: float, direction: int):
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
        if angle < 45.0: 
            return 45.0 
        elif angle > 135.0:
            return 135.0
        return angle
    
    def __checkSpeed(self, speed: int) -> int:
        if speed < -100:
            return -100
        elif speed > 100:
            return 100
        return speed
    
    def drive(self, speed: Optional[int], angle: Optional[float]):
        if angle is not None:
            self.steering_angle = angle
        if speed is not None:
            self.speed = speed

        self.__fw.turn(self.steering_angle)
        self.__bw.speed(self.speed)

        if self.speed > 0:
            self.__bw.forward()
            self.__direction = 1
        elif self.speed < 0:
            self.__bw.backward()
            self.__direction = -1
        else:
            self.stop()

    def stop(self):
        self.__bw.stop()
        self.__direction = 0

            
if __name__ == '__main__' :

    
    car = BaseCar()

    #**********************

    car.steering_angle = -50
    print(f"steering_angle: {car.steering_angle}")

    car.steering_angle = -45
    print(f"steering_angle: {car.steering_angle}")

    car.steering_angle = 50
    print(f"steering_angle: {car.steering_angle}")

    car.steering_angle = 135
    print(f"steering_angle: {car.steering_angle}")

    car.steering_angle = 150
    print(f"steering_angle: {car.steering_angle}")
        
    

