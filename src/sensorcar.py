from basecar import BaseCar
from basisklassen import Infrared
from soniccar import SonicCar
import numpy
import time
import util.json_loader as loader
import json


class SensorCar(SonicCar):
    '''
    Die Klasse SensorCar verfolgt mit Hilfe von Infrarot-Sensoren eine schwarze Linie auf dem Boden. 

    Mehtoden:
        follow_line_analog - nutzt zur Auswertung die analogen Werte des Infrarot-Sensors
        reference_ground - erzeugt Config-Werte für die Bodenbeschaffenheit
        follow_line_digital - nutzt zur Auswertung die digitalen Werte des Infrarot-Sensors

    '''
    def __init__(self, steering_angle = 90, speed = 0):
        super().__init__(steering_angle, speed)
        self.__irm = Infrared()
        cfg = loader.readjson("/home/pi/Documents/git/c2c_project_1/src/config/car_hardware_config.json")
        self.__irm.set_references(ref=cfg["infrared_reference"]) # setzen der Referenzwerte aus der Hareware-Config


    def follow_line_analog(self,geschwindigkeit: int= 30):
        '''
        Basierend auf den digitalen Werten der Infarotsensoren wird der schwarzen Linie gefolgt.
        '''
        sumlist= []
        while True:
            data = self.__irm.get_average()
            sumlist.append(round(numpy.sum(data),1))    # Aufbau der Summenliste zur Auswertung des Abbruchs
            # Bestimmung der Lenkwinkel
            if min(data) == data[2]: self.drive(speed=geschwindigkeit, angle=90)
            elif min(data) == data[0]:self.drive(speed=geschwindigkeit, angle=(45))
            elif min(data) == data[1]:self.drive(speed=geschwindigkeit, angle=68)
            elif min(data) == data[3]:self.drive(speed=geschwindigkeit, angle=(109))
            elif min(data) == data[4]:self.drive(speed=geschwindigkeit, angle=(135))
            # Abbruch Bedingungen
            if len(sumlist) >= 2 and sumlist[len(sumlist)-1]-(numpy.mean(sumlist)*0.1) > sumlist[len(sumlist)-2] : break
        self.stop()

    def reference_ground(self):
        '''
        Die Referenz des Fußbodes wird in dieser Methode neu evaluiert und in die Hardware-Config geschrieben.

        Return:
            keine
        '''
        sumlist= []
        start_zeit = time.time()
        while time.time() - start_zeit < 2: # feste Zeit zum erzuegen der Referenzwerte des Bodens
            data = self.__irm.get_average()
            sumlist.append(round(numpy.sum(data),1)) # Aufbau der Summenliste
        reference_list = [round(numpy.mean(sumlist)/len(data)*0.8,1) for _ in range(len(data))]  # erzeugen der neuen Referenzliste
        self.__irm.set_references(reference_list)
        # alte Hardware-Config lesen
        with open("src/config/car_hardware_config.json", "r") as f:
                data = json.load(f)

        data["infrared_reference"] = reference_list
        # neue Referenzliste in die Hardware-Config schreiben
        with open("src/config/car_hardware_config.json", "w") as f:
            json.dump(data, f, indent= 2) 


    def follow_line_digital(self,geschwindigkeit: int= 30):
        '''
        Basierend auf den digitalen Werten der Infarotsensoren wird der schwarzen Linie gefolgt.
        Die Mehtode wertet auch den Abstand aus, bei einem Hindernis wird die Fahrt gestoppt. 
        '''
        while True:
            data = self.__irm.read_digital()
            print(data)
            distance = self.get_distance() # Überprüfen der Distanz zu einem Hindernis
            if numpy.sum(data) > 2  or distance < 20 : # Abbruchbedingungen
                print(data)
                print(distance)
                break
            # Lenkwinkelbedingungen
            elif data == [1,0,0,0,0]: self.drive(speed=geschwindigkeit*0.6, angle=45)
            elif data == [1,1,0,0,0] or data == [0,1,0,0,0]: self.drive(speed=geschwindigkeit*0.8, angle=68)
            elif data == [0,0,1,0,0] or data == [0,0,0,0,0] : self.drive(speed=geschwindigkeit, angle=90)
            elif data == [0,0,0,1,1] or data == [0,0,0,1,0]: self.drive(speed=geschwindigkeit*0.8, angle=109)
            elif data == [0,0,0,0,1] : self.drive(speed=geschwindigkeit*0.6, angle=135)  
        self.stop()


if __name__ == "__main__":
    car = SensorCar()
    #car.test_infrared(10)
    #car.follow_line_analog(60)
    #car.reference_ground()
    car.follow_line_digital(60)
    #car.stop()