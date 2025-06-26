from basecar import BaseCar
from soniccar import SonicCar
from basisklassen import Ultrasonic
from basisklassen import Infrared 
import numpy
import time

class SensorCar(SonicCar):

    def __init__(self, steering_angle: int = 90, speed: int = 0):

        super().__init__(steering_angle, speed)
        self.__ir = Infrared()
        self.__ir.set_references([20,20,20,20,20])
  

    # def get_irmessung(self):
    #     irmessung=self.__ir.read_digital()
    #     if irmessung == [1,1,1,1,1]:
    #         self.stop()
    #     return irmessung

#Erforderliche Funktionen: Fahrmodus 4,5,6
#Vorhandene Funktionen: read_digital, read_analog, get_average, set_reference, cali_reference

    #def follow_line(self, geschwindigkeit: int=None):
    

            # Optional: Status loggen
         #   self._log_status()


    def stop(self):
        '''
        Überschreibt die stop-Methode von BaseCar, um die Datenaufzeichnung hinzuzufügen.
        '''
        # Wichtig: Erst Geschwindigkeit im internen Zustand anpassen, dann stoppen
        super().stop()
        #self.__us.stop()  # Ultraschallsensor stoppen, falls nötig
        self._log_status()

    # --- Implementierung der geforderten Fahrmodi ---

    def follow_line(self):
        # Überprüfe die Entfernung mit der SonicCar-Funktion
        MIN_DISTANCE = 5
        while True:
            try:
                distance = self.get_distance()
                if distance < MIN_DISTANCE:
                    print(f"Abstand zu gering: {distance} cm. Fahrzeug wird gestoppt!")
                    self.stop()
                    break
                
                # Liest die digitalen Werte der Infrarotsensoren
                sensor_values = self.__ir.read_digital()  # Beispiel: [0, 0, 1, 1, 0]
                sensor_values_analog = self.__ir.read_analog()
                print(f"Sensordaten: {sensor_values}")
                print(f"Sensordaten: {sensor_values_analog}")
                

                    
                if sensor_values == [0, 0, 0, 0, 0]:
                    self.drive(speed=20, angle=90)
                elif sensor_values == [0, 0, 1, 0, 0]:
                    self.drive(speed=20, angle=90)
                elif sensor_values == [0, 0, 1, 1, 0]:
                    self.drive(speed=20, angle=115)
                elif sensor_values == [0, 0, 0, 1, 0]:
                    self.drive(speed=20, angle=125)
                elif sensor_values == [0, 0, 0, 1, 1]:
                    self.drive(speed=20, angle=125)
                elif sensor_values == [0, 0, 0, 0, 1]:
                    self.drive(speed=20, angle=135)
                elif sensor_values == [0, 1, 1, 0, 0]:
                    self.drive(speed=20, angle=70)
                elif sensor_values == [1, 1, 0, 0, 0]:
                    self.drive(speed=20, angle=55)
                elif sensor_values == [0, 1, 0, 0, 0]:
                    self.drive(speed=20, angle=55)
                elif sensor_values == [1, 0, 0, 0, 0]:
                    self.drive(speed=20, angle=45) 
                else:
                    # Keine Linie erkannt -> Stoppen
                    self.stop()
                    print("Linie verloren. Fahrzeug gestoppt.")
                    break

                # Optional: Pause einfügen, um die Ausgabe lesbar zu machen
                time.sleep(0.1)
                
            except KeyboardInterrupt:
                # Beenden bei Tastendruck (Ctrl+C)
                print("Linienverfolgung beendet.")
                break
        
    def test_infrared(self):
        '''
        Testet die Infrarotsensorik, indem die Werte der Sensoren ausgelesen und ausgegeben werden.
        '''
        print("Starte Infrarotsensor-Test...")
        for i in range(10):
            sensor_values = self.__ir.read_analog()  # Liest die digitalen Werte der Sensoren
            print(f"Infrarotsensor-Werte: {sensor_values}")

        print(self.__ir.set_references)
        for i in range(10):
            sensor_values = self.__ir.read_digital()  # Liest die digitalen Werte der Sensoren
            print(f"Infrarotsensor-Werte: {sensor_values}")


if __name__ == "__main__":
    car = SensorCar()
    #car.test_infrared()
    car.follow_line()

