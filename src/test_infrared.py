#test_infrared.py
from basisklassen import Infrared
from soniccar import SonicCar
import numpy as np
 
ir=Infrared()
offset_2=0
offset_3=0
ini_ref=ir._references
print(f"ini_ref: {ini_ref}")
single_sensor_ave=ir.get_average()
print(f"single_sensor_ave: {single_sensor_ave}")
all_sensor_ave=np.mean(single_sensor_ave)
print(f"all_sensor_ave: {all_sensor_ave}")
#delta_single_sensor = ir.get_average() - np.mean(ir.get_average())
delta_single_sensor = single_sensor_ave - all_sensor_ave
print(f"delta_single_sensor: {delta_single_sensor}")
for i in range(-30,31,1):
    mw_offset=i
    ir.set_references(ini_ref)
    new_ref = (all_sensor_ave-(delta_single_sensor)) + mw_offset
    ir.set_references(new_ref)
    quersumme_= np.sum(ir.read_digital())
 
    if quersumme_ == 2:
        offset_2=mw_offset
    if quersumme_ == 3:
        offset_3 = mw_offset
        break
 
print("--------Reference_festlegen------------------------------")
mw_offset=(offset_2+offset_3)/2
#new_ref = (all_sensor_ave-(delta_single_sensor)) + mw_offset
 
#new_ref = (all_sensor_ave-[0,0,0,0,0]) + mw_offset-10
new_ref = [28, 28, 28, 28, 28]  # Set a fixed reference for testing
print("Check new reference:")
ir.set_references(new_ref)
print(ir._references)
print(ir.read_digital())
print(ir.read_analog())

'''Check new reference:
[28, 28, 28, 28, 28] reference
[0, 1, 1, 0, 0]
[35, 20, 18, 33, 37] analog
analog - reference: legt digital fest
z.B. 35-28 = 7 <- positive -> daraus folgt digital == 0 -> weg von der linie
 20-28 = -8 <- negativ -> daraus folgt digital == 1 -> da ist eine Linie
[1, 1, 1, 1, 1] -> stop komplett auf der stoplinie
Hinweis:Da meist alle nicht auf der Linie sind, ist es sinnvoll, die quersumme > 3 dann stop linie
[0, 1, 1, 0, 0] -> leicht links -> wir verfolgen die 1 <- die 1 soll immer bei pos-3
- Config-Datei anpassen, damit die Referenzwerte [28, 28, 28, 28, 28] gesetzt werden
'''