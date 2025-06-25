from basecar import BaseCar
from basisklassen import Infrared
import numpy
import time
import util.json_loader as loader
import json

class SensorCar(BaseCar):
    def __init__(self, steering_angle = 90, speed = 0, direction = 0):
        super().__init__(steering_angle, speed, direction)
        self.__irm = Infrared()
        cfg = loader.readjson("/home/pi/Documents/git/c2c_project_1/src/config/car_hardware_config.json")
        self.__irm.set_references(ref=cfg["infrared_reference"])

    
    def follow_line_analog(self,geschwindigkeit: int= None):
        sumlist= []
        while True:
             data = self.__irm.get_average()
             sumlist.append(round(numpy.sum(data),1))
             print("{}.{}".format(sumlist[len(sumlist)-1],data))
             if min(data) == data[2]: self.drive(speed=geschwindigkeit, angle=90)
             elif min(data) == data[0]:self.drive(speed=geschwindigkeit, angle=(45))
             elif min(data) == data[1]:self.drive(speed=geschwindigkeit, angle=68)
             elif min(data) == data[3]:self.drive(speed=geschwindigkeit, angle=(109))
             elif min(data) == data[4]:self.drive(speed=geschwindigkeit, angle=(135))
             if len(sumlist) >= 2 and sumlist[len(sumlist)-1]-(numpy.mean(sumlist)*0.1) > sumlist[len(sumlist)-2] : break
        self.stop()
        print(sumlist)
    
    def test_infrared(self, anzahl: int=1):
          for i in range(anzahl):
               self.__irm.test()

    def reference_ground(self):
          sumlist= []
          start_zeit = time.time()
          while time.time() - start_zeit < 2:
               data = self.__irm.get_average()
               sumlist.append(round(numpy.sum(data),1))
          reference = round(numpy.mean(sumlist)/len(data)*0.8,1)
          reference_list = [reference for _ in range(len(data))]
          self.__irm.set_references(reference_list)
          with open("/home/pi/Documents/git/c2c_project_1/src/config/car_hardware_config.json", "r") as f:
                    data = json.load(f)

          data["infrared_reference"] = reference_list

          with open("/home/pi/Documents/git/c2c_project_1/src/config/car_hardware_config.json", "w") as f:
               json.dump(data, f, indent= 2) 

    
    def follow_line_digital(self,geschwindigkeit: int= None):
          while True:
               data = self.__irm.read_digital()
               print(data)
               if numpy.sum(data) > 2: break
               elif data == [1,0,0,0,0]: self.drive(speed=geschwindigkeit*0.8, angle=45)
               elif data == [1,1,0,0,0] or data == [0,1,0,0,0]: self.drive(speed=geschwindigkeit, angle=68)
               elif data == [0,0,1,0,0] or data == [0,0,0,0,0] : self.drive(speed=geschwindigkeit, angle=90)
               elif data == [0,0,0,1,1] or data == [0,0,0,1,0]: self.drive(speed=geschwindigkeit, angle=109)
               elif data == [0,0,0,0,1] : self.drive(speed=geschwindigkeit*0.8, angle=135)
          self.stop()


if __name__ == "__main__":
        car = SensorCar()
        #car.test_infrared(10)
        #car.follow_line_analog(60)
        #car.reference_ground()
        car.follow_line_digital(60)
        #car.stop()