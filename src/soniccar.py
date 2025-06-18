from basecar import BaseCar
from basisklassen import Ultrasonic 
import time

class SonicCar(BaseCar):
    '''
    Die SonicCar Klasse erbt von der Klasse BaseCar die Grundfahrfunktionen des Fahrzeuges und ergänzt diese um die Funktionen des UltraSchallsensors.

    Methoden:
        get_distance - gibt den Abstand zu einem Hindernis zurück
        stop - setzt speed zu 0 und fährt den Ultraschallsensor runter
        Fahrmodi Methode
            drive_mode_obsticale_stop - stoppt bei einem Hindernis
            drive_mode_exploration_tour - versucht ein Hindernis zu umfahren

    
    Begrenzungswerte:
        Der Mindestabstand ist gesetzt
        
    '''  
    mindestabstand = 5
    
    def __init__(self, steering_angle = 0, speed = 0, direction = 0):
        super().__init__(steering_angle, speed, direction)
        self.__usm = Ultrasonic()

    def stop(self):
        '''
        Die Methode stop() übernimmt die Argumente der Methode stop() aus der BaseCar-Klasse und erweitert diese um 
        die stop-Methoden von Ultrasonic.

        Return-Value:
            Es werden keine Werte übergeben.
        '''
        super().stop()
        self.__usm.stop()

    def get_distance(self):
        '''
        Die Methode get_distance gibt den Abstand zu einem Hindernis zurück. Die Werte sind in cm.

        Return Value:
            distance als Integer
        '''
        try:
            distance = self.__usm.distance()
            if distance < 0 : raise Exception
        except :
            if distance == -1 : print("Low signal and timeout reached")
            if distance == -2 : # Die Fehler werden geworfen, wenn offener Raum vor dem Auto ist.
                distance = self.mindestabstand + 1 # Korrektur des Rückgabewertes auf den Mindestabstand + 1
                print("High signal and timeout reached") 
            if distance == -3 : print("Negative distance")
            if distance == -4 : # Die Fehler werden geworfen, wenn offener Raum vor dem Auto ist.
                distance = distance = self.mindestabstand + 1
                print("Error in time measurement")
        finally:
            return distance

    def drive_mode_obsticale_stop(self, speed: int = None, angle: int = 90, fahrzeit: int=1, abstand: int = None):
        '''
        Die Methode drive_mode_obsticale_stop fährt in einer gegeben Geschwindigkeit, einem gegebenen Lenkwinkel (Defaultwert geradeaus), 
        einer gegeben Zeit (Defaultwert 1 Sekunde) und einem gegebenen Abstand (Mindestabstand definiert in der Klasse) auf ein Hindernis zu. 
        Die Fahrt wird gestoppt, wenn enteder der Abstand unterschritten wird oder die Fahrzeit abgelaufen ist.
        '''
        if abstand is None: abstand = self.mindestabstand
        start_fahrzeit = time.time()
        if speed < 0 : print("Rückwärtsfahrt übergeben - wurde seitens des Programms auf Vorwärtsfahrt geändert um einen Unfall zu vermeiden.")
        super().drive(abs(speed), angle) # speed wird immer als Absolutwert genommen, um immer vorwärts zufahren, da die Sensoren vorn verbaut sind.
        while time.time() - start_fahrzeit < fahrzeit:
            if self.get_distance() <= abstand:
                break        
        self.stop()

    def drive_mode_exploration_tour(self, speed: int = None, angle: int = 90, fahrzeit: int=10, abstand: int=None):
        '''
        Die Methode drive_mode_exploration_tour fährt in einer gegeben Geschwindigkeit, einem gegebenen Lenkwinkel (Defaultwert geradeaus), 
        einer gegeben Zeit (Defaultwert 10 Sekunde) und einem gegebenen Abstand (Mindestabstand definiert in der Klasse) umher und dedektiert Hindernisse. 
        Die Fahrt wird gestoppt und versucht dem Hindernis auszuweichen, wenn enteder der Abstand unterschritten wird. Alternative wird nach Ablauf der
        Fahrzeit ebenfalls die Methode beendet.
        '''
        if abstand is None: abstand = self.mindestabstand
        start_fahrzeit = time.time()
        if speed < 0 : print("Rückwärtsfahrt übergeben - wurde seitens des Programms auf Vorwärtsfahrt geändert um einen Unfall zu vermeiden.")
        super().drive(abs(speed), angle) # speed wird immer als Absolutwert genommen, um immer vorwärts zufahren, da die Sensoren vorn verbaut sind.
        while time.time() - start_fahrzeit < fahrzeit:
            if self.get_distance() <= abstand:
                super().drive(abs(speed)*-1, 135)
                time.sleep(2)
            super().drive(abs(speed), angle)
        self.stop()

if __name__ == '__main__':

    car = SonicCar()
    car.drive_mode_exploration_tour(30)

    # car.drive_mode_obsticale_stop(60,90,10, 10)
    # car.drive(-30,90)
    # time.sleep(2)
    # # for i in range(10):
    # #     print(car.get_distance())

    # car.stop()