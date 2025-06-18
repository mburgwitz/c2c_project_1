from basecar import BaseCar
from basisklassen import Ultrasonic 
import time

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
            if distance < 0 : raise Exception
        except :
            if distance == -1 : print("Low signal and timeout reached")
            if distance == -2 : print("High signal and timeout reached")
            if distance == -3 : print("Negative distance")
            if distance == -4 : print("Error in time measurement")
        finally:
            return distance

    def drive_mode_obsticale_stop(self, speed: int = None, angle: int = 90, fahrzeit: int=1, abstand: int=5):
        '''
        Die Methode drive_mode_obsticale_stop fährt in einer gegeben Geschwindigkeit, einem gegebenen Lenkwinkel (Defaultwert geradeaus), 
        einer gegeben Zeit (Defaultwert 1 Sekunde) und einem gegebenen Abstand (Defaultwert 5 cm) auf ein Hindernis zu. 
        Die Fahrt wird gestoppt, wenn enteder der Abstand unterschritten wird oder die Fahrzeit abgelaufen ist.
        '''
        start_fahrzeit = time.time()
        if speed < 0 : print("Rückwärtsfahrt übergeben - wurde seitens des Programms auf Vorwärtsfahrt geändert um einen Unfall zu vermeiden.")
        super().drive(abs(speed), angle) # speed wird immer als Absolutwert genommen, um immer vorwärts zufahren, da die Sensoren vorn verbaut sind.
        while time.time() - start_fahrzeit < fahrzeit:
            if self.get_distance() <= abstand:
                break
        super().stop()

    def drive_mode_exploration_tour(self, speed: int = None, angle: int = 90, fahrzeit: int=10, abstand: int=5):
        start_fahrzeit = time.time()
        if speed < 0 : print("Rückwärtsfahrt übergeben - wurde seitens des Programms auf Vorwärtsfahrt geändert um einen Unfall zu vermeiden.")
        super().drive(abs(speed), angle) # speed wird immer als Absolutwert genommen, um immer vorwärts zufahren, da die Sensoren vorn verbaut sind.
        while time.time() - start_fahrzeit < fahrzeit:
            if self.get_distance() <= abstand or self.get_distance() == -2:
                super().drive(abs(speed)*-1, 135)
                time.sleep(1)
            super().drive(abs(speed), angle)
        super().stop()

if __name__ == '__main__':

    car = SonicCar()
    #car.drive_mode_exploration_tour(30)

    car.drive_mode_obsticale_stop(30,90,10)
    car.drive(-30,90)
    # time.sleep(2)
    # for i in range(10):
    #     print(car.get_distance())

    car.stop()