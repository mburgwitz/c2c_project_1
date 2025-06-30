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
        """
        Initialize SensorCar with infrared sensor and load hardware configuration.

        Calls superclass constructors to set up drive and ultrasonic features,
        then instantiates an Infrared sensor and applies reference values from
        the hardware config file.

        Parameters
        ----------
        steering_angle : int, optional
            Initial steering angle (default is 90, straight ahead).
        speed : int, optional
            Initial speed (default is 0).
        """

        super().__init__(steering_angle, speed)
        self.__irm = Infrared()
        cfg = loader.readjson("src/config/car_hardware_config.json")
        self.__irm.set_references(ref=cfg["infrared_reference"]) # setzen der Referenzwerte aus der Hareware-Config

    def get_line_status(self) -> list:
        """
        Read digital values from the five infrared sensors indicating line presence.

        Returns
        -------
        list of int
            A list of five binary values (0 or 1), where 1 indicates the sensor
            detects the line and 0 indicates background.
        """
        return self.__irm.read_digital()
    
    def follow_line_analog(self,geschwindigkeit: int= 30):
        """
        Follow a line using analog IR sensor readings until the line is lost.

        Continuously reads averaged analog values, determines steering angle
        based on the sensor with the minimum reading, and drives accordingly.
        Recording stops when a significant deviation from the mean signal
        indicates the line is no longer detected.

        Parameters
        ----------
        geschwindigkeit : int, optional
            Speed at which to follow the line (default is 30).
        """
        sumlist= []
        self._stop_event.clear()
        self._running = True
        while(self._running):
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
        self._running = False

    def reference_ground(self):
        """
        Re-evaluate the surface reference values for the infrared sensors.

        Samples averaged IR readings for two seconds, computes new baseline
        thresholds, and writes them back into the hardware config JSON file.
        """
        sumlist= []
        start_zeit = time.time()
        while time.time() - start_zeit < 2: # feste Zeit zum erzuegen der Referenzwerte des Bodens
            data = self.__irm.get_average()
            sumlist.append(round(numpy.sum(data),1)) # Aufbau der Summenliste
        reference_list = [round(numpy.mean(sumlist)/len(data)*0.8,1) for _ in range(len(data))]  # erzeugen der neuen Referenzliste
        # alte Hardware-Config lesen
        with open("src/config/car_hardware_config.json", "r") as f:
                data = json.load(f)

        data["infrared_reference"] = reference_list
        # neue Referenzliste in die Hardware-Config schreiben
        with open("src/config/car_hardware_config.json", "w") as f:
            json.dump(data, f, indent= 2) 

        print("reference_ground")

    def follow_line_digital(self,geschwindigkeit: int= 30, stop_distance: int = 20):
        '''
        Follow a line using digital IR sensor readings until completion or obstacle.

        Reads digital sensor values and ultrasonic distance in a loop,
        adjusts speed and steering based on discrete pattern matching,
        and stops when an obstacle is within `stop_distance` or too many
        sensors detect the line (junction).

        Parameters
        ----------
        geschwindigkeit : int, optional
            Base speed for line following (default is 30).
        stop_distance : int, optional
            Distance in cm at which to stop when an obstacle is detected
            (default is 20).
        '''
        self._stop_event.clear()
        self._running = True
        while(self._running):
            data = self.__irm.read_digital()
            distance = self.get_distance() # Überprüfen der Distanz zu einem Hindernis
            if numpy.sum(data) > 2  or distance < stop_distance and self._running: # Abbruchbedingungen
                self.stop()
                self._running = False
                break
            # Lenkwinkelbedingungen
            elif data == [1,0,0,0,0]: self.drive(speed=geschwindigkeit*0.6, angle=45)
            elif data == [1,1,0,0,0] or data == [0,1,0,0,0]: self.drive(speed=geschwindigkeit*0.8, angle=68)
            elif data == [0,0,1,0,0] or data == [0,0,0,0,0] : self.drive(speed=geschwindigkeit, angle=90)
            elif data == [0,0,0,1,1] or data == [0,0,0,1,0]: self.drive(speed=geschwindigkeit*0.8, angle=109)
            elif data == [0,0,0,0,1] : self.drive(speed=geschwindigkeit*0.6, angle=135)  

            time.sleep(0.2)
        
if __name__ == "__main__":
    car = SensorCar()
    car.follow_line_digital(60)
