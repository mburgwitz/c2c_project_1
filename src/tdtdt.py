from basisklassen import Infrared
from soniccar import SonicCar
import numpy as np


ir=Infrared()
offset_2=0
offset_3=0
ini_ref=ir._references
single_sensor_ave=ir.get_average()
all_sensor_ave=np.mean(single_sensor_ave)
#delta_single_sensor = ir.get_average() - np.mean(ir.get_average())
delta_single_sensor = single_sensor_ave - all_sensor_ave

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

new_ref = (all_sensor_ave-[0,0,0,0,0]) + mw_offset
print("Check new reference:")
ir.set_references(new_ref)
print(ir._references)
print(ir.read_digital())


   
# ir=Infrared()

# ini_ref=ir._references
# single_sensor_ave=ir.get_average()
# all_sensor_ave=np.mean(single_sensor_ave)
# #delta_single_sensor = ir.get_average() - np.mean(ir.get_average())
# delta_single_sensor = single_sensor_ave - all_sensor_ave

# for i in range(-30,31,1):
#     mw_offset=i
#     ir.set_references(ini_ref)
#     new_ref = (all_sensor_ave-(delta_single_sensor)) + mw_offset
#     ir.set_references(new_ref)
#     quersumme_= np.sum(ir.read_digital())

#     if quersumme_ == 2:
#         offset_2=mw_offset
#     if quersumme_ == 3:
#         offset_3 = mw_offset
#         break
  
# print("--------Reference_festlegen------------------------------")
# mw_offset=(offset_2+offset_3)/2
# new_ref = (all_sensor_ave-(delta_single_sensor)) + mw_offset
# print("Check new reference:")
# ir.set_references(new_ref)
# print(ir._references)
# print(ir.read_digital())



