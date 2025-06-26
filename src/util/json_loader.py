import json
import pandas as pd
 
def readjson(file2read= "car_hardware_config.json"):
    try:
        with open (file2read,"r", encoding="utf-8") as file:
            wasdrinsteht=json.load(file)

        return wasdrinsteht
    except Exception as e:
        raise Exception(e)
     
if __name__ == "__main__":
    input=readjson()
    t_off=input["turning_offset"]
    f_A=input["forward_A"]
    f_B=input["forward_B"]  
#    print(t_off)
 