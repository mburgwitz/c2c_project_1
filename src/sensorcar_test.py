from basisklassen import Infrared
from soniccar import SonicCar
import numpy as np
import time


class SensorCar(SonicCar):
    def __init__(self, steering_angle = 90, speed = 0):
        super().__init__(steering_angle, speed)
        self.__ir=Infrared()
        self.print_ref_ir()

 #       self.__ir.set_references([32,32,32,32,32])


    def print_ref_ir(self):
        return print(f"Reference-Werte: {self.__ir._references}")
    
    def set_ref_ir(self,value: int = None, offset: int=None):
        if offset is None:
            offset = 0      
        if value is not None:
            value=value+offset
            print(f"value als Funktionsparameter + offset= {value}")
        else:
            value =self.get_ref_average()+offset
            print(f"value als mittelwert der Sensormessung + offset= {value}")
        self.__ir.set_references([value,value,value,value,value])
 #       return self.print_ref_ir()

    def get_ref_average(self):
        return np.mean(self.__ir.get_average())
    
     
    def __get_irstreuung(self):
        self.single_sensor_ave=self.__ir.get_average()
        self.all_sensor_ave=np.mean(single_sensor_ave)
        return (self.single_sensor_ave - self.all_sensor_ave)
    
    # def set_irref(self, Streuung: bool=False):
    #     offset_2 = [0,0,0,0,0]
    #     offset_3 = [0,0,0,0,0]
    #     single_sensor_ave=self.__ir.get_average()
    #     all_sensor_ave=np.mean(single_sensor_ave)
    #     for i in range(-30,31,1):
    #         offset=i
    #         self.__ir.set_references([300,300,300,300,300])
    #         if Streuung:
    #             new_ref = (all_sensor_ave-self.__get_irstreuung()) + offset
    #         else:
    #             new_ref = (all_sensor_ave-[0,0,0,0,0]) + offset
    #         self.__ir.set_references(new_ref)
    #         quersumme_= np.sum(self.__ir.read_digital())

    #         if quersumme_ == 2:
    #             offset_2 = offset
    #         if quersumme_ == 3:
    #             offset_3 = offset
    #             break
      
    #     print("--------Reference_festlegen------------------------------")
    #     offset=(offset_2 + offset_3)/2
    #     if Streuung:
    #         new_ref = (all_sensor_ave-self.__get_irstreuung()) + offset
    #     else:
    #         new_ref = (all_sensor_ave-[0,0,0,0,0]) + offset
    #     print("Check new reference:")
    #     self.__ir.set_references(new_ref)
    #     print(self.__ir._references)
    #     print(self.__ir.read_digital())

    def get_irmessung(self):
        irmessung=self.__ir.read_digital()
        irquersumme= np.sum(irmessung)
        print(f"IR-Messung: {irmessung}")
        if irquersumme > 3:
            self.stop()
#        return irmessung, irquersumme
        return irmessung 

    def hold_the_line(self, geschwindigkeit=100):
   
        if self.irmessung== [1,0,0,0,0]:
            self.drive(speed=geschwindigkeit*0.4, angle = self.steering_angle+20)

        if self.irmessung== [1,1,0,0,0]: 
            self.drive(speed=geschwindigkeit*0.6, angle = self.steering_angle+15)

        if self.irmessung == [0,1,0,0,0]:  
            self.drive(speed=geschwindigkeit*0.8, angle = self.steering_angle+10)

        if self.irmessung == [0,1,1,0,0]: 
            self.drive(speed=geschwindigkeit*0.9, angle = self.steering_angle+5)

        if self.irmessung == [0,0,1,0,0]: 
            self.drive(speed=geschwindigkeit, angle = self.steering_angle)

        if self.irmessung == [0,0,1,1,0]:
            self.drive(speed=geschwindigkeit*0.9, angle = self.steering_angle-5)

        if self.irmessung == [0,0,0,1,0]:
            self.drive(speed=geschwindigkeit*0.8, angle = self.steering_angle-10)

        if self.irmessung == [0,0,0,1,1]:
            self.drive(speed=geschwindigkeit*0.6, angle = self.steering_angle-15)

        if self.irmessung == [0,0,0,0,1]:    
            self.drive(speed=geschwindigkeit*0.4, angle = self.steering_angle-20)

        time.sleep(warten)

    def drivemode_middle_line(self, geschwindigkeit, lenkwinkel):
        self.drive(speed=geschwindigkeit, angle=lenkwinkel)
        while True:
            self.get_irmessung()

            self.hold_the_line()




if __name__ == "__main__":
    ircar = SensorCar()
    ircar.set_ref_ir(offset=-10)
    ircar.print_ref_ir()
#    Drive=True
#    while True:
    for i in range (10):
        ircar.get_irmessung()
#        time.sleep(10)
#        break







    
 #   ircar2.set_irref()
