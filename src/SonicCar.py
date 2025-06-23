from basecar import BaseCar
from basisklassen import Ultrasonic

class SonicCar(BaseCar): 
    def __init__(self, steering_angle: float = 90.0, speed: float = 0, direction: int = 0): #Distance hinzugefügt um zu initalisieren
        super().__init__(steering_angle, speed, direction)

        self.us = Ultrasonic()

    def get_distance(self):
        return self.us.distance()

if __name__ == "__main__":   
    car = SonicCar()

    try:
        car.drive(speed = 30, angle = 90)
        print("car is driving")

        while True:
            distance = car.get_distance()
            print(f"Distance to obstacle: {distance}")

            if distance <= 5:
                print (f"Obstacle detected! Stop car")
                car.stop()
                break
    except Exception as e:
        print(f"Error reading distance: {e}")
        car.stop()
        break