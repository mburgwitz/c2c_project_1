from basecar import BaseCar
from basisklassen import Ultrasonic


class SonicCar(BaseCar):
    def __init__(self, steering_angle = 0, speed = 0, direction = 0):
        super().__init__(steering_angle, speed, direction)
        self.__usm = Ultrasonic()

    def stop(self):
        super().stop()
        self.__usm.stop()

    def get_distance(self):
        try:
            distance = self.__usm.distance()
        except distance < 0 :
            if distance == -1 : print("Low signal and timeout reached")
            if distance == -2 : print("High signal and timeout reached")
            if distance == -3 : print("Negative distance")
            if distance == -4 : print("Error in time measurement")
        else:
            return distance


if __name__ == '__main__':
    car = SonicCar()
    for i in range(10):
        print(car.get_distance())

car.stop()