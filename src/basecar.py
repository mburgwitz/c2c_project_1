from basisklassen import FrontWheels, BackWheels
import time

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
    MAX_STEERING_ANGLE = 135
    MIN_STEERING_ANGLE = 45

    MAX_SPEED = 100
    MIN_SPEED = -100

    def __init__(self, steering_angle: int = 90.0, speed: int = 0.0, direction: int = 0):
        self.__steering_angle = steering_angle
        self.__speed = speed
        self.__direction = direction  
        self.__fw = FrontWheels()
        self.__bw = BackWheels()      

    @property
    def steering_angle(self):
        return self.__steering_angle
    
    @steering_angle.setter
    def steering_angle(self, new_angle: int):
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
    
    def __checkSteeringAngle(self, angle: int) -> int:
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
        if angle is not None:
            self.__steering_angle = angle
        if speed is not None:
            self.__speed = speed

        if self.__speed > 0:
            self.__bw.forward()
            self.__direction = 1
        elif self.__speed < 0:
            self.__bw.backward()
            self.__direction = -1
        else:
            self.stop()

        self.__fw.turn(self.__steering_angle)
        self.__bw.speed = abs(self.__speed)        

    def stop(self):
        '''
        Die stop-Methode setzt die Geschwindigkeit auf 0 

        Parameter:
            keine Parameter

        Return-Value:
            gibt keinen Wert zurück

        '''
        self.__bw.stop()
        self.__direction = 0
    
    def fahrmodus1(self, geschwindigkeit, fahrzeit):
        self.drive(speed = geschwindigkeit, angle = 90)
        time.sleep(fahrzeit/2)
        self.drive(speed = geschwindigkeit *-1, angle = 90)
        time.sleep(fahrzeit/2)
        self.stop()


if __name__ == '__main__':

    car = BaseCar()
    car.fahrmodus1(30, 4)
    # car.drive(30, 90)
    # time.sleep(2)
    # car.stop()
    # car.drive(-30, 45)
    # time.sleep(2)
    # car.drive(0, 90)
    # car.stop()