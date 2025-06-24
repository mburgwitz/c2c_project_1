from basecar import BaseCar
from basisklassen import Ultrasonic
from util.config.manager import ConfigManager
import time
from typing import List, Union, Tuple
from util.logger import Logger

class SonicCar(BaseCar):

    def __init__(self, cfg_name: str = 'car_initial_values.json'):
        super().__init__(cfg_name)

        self.log = Logger.get_logger("SonicCar") 

        self.log.debug('init sonicCar')

        self.log.debug('get ultrasonic conf')
        # us_conf = ConfigManager.get("ultrasonic",name=cfg_name )
        # self.__us = Ultrasonic(preparation_time = us_conf['preparation_time'],
        #                        impuls_length = us_conf['impuls_length'],
        #                        timeout = us_conf['impuls_length']
        #                         )
        
        us_conf = ConfigManager.get(as_attr=True, name=cfg_name )
        # self.__us = Ultrasonic(preparation_time = us_conf.ultrasonic['sensor']['preparation_time'],
        #                        impuls_length = us_conf.ultrasonic['sensor']['impuls_length'],
        #                        timeout = us_conf.ultrasonic['sensor']['impuls_length']
        #                         )
        self.__us = Ultrasonic()
        
        self.__us_poll_time = 0.25# us_conf.ultrasonic.polltime

        self.__us_error_description = { -1: "Low signal and timeout reached",
                                        -2: "High signal and timeout reached",
                                        -3: "Negative distance",
                                        -4: "Error in time measurement"}

        self.log.debug(f'ultrasonic conf: {us_conf}')

        self.drive_log = dict()

        

    def get_distance(self, ignore_error: bool = False, types_to_ignore: List[int] = [-1,-2]) -> Union[Tuple[int, bool], None]:
        distance = self.__us.distance()
        
        error_occured = False
        # just return None if error occured
        if ignore_error:
            distance = None if distance < 0 else distance
        else:
            # -1: Low signal and timeout reached
            if distance < 0:
                self.log.info(f"Error {distance} measuring distance: {self.__us_error_description[distance]}")
                if distance not in types_to_ignore:
                    
                    error_occured = True
                    self.log.info(f"Handling Error")
                    if distance == -1:
                        self.log.info(f"...Error {-1}: ")
                    elif distance == -2:
                        self.log.info(f"...Error {-2}: ")
                    elif distance == -3:
                        self.log.info(f"...Error {-3}: Stopping.")
                    elif distance == -4:
                        self.log.info(f"...Error {-4}: Stopping.")
                    else:
                        self.stop()
                        raise ValueError(f"Error code {distance} unknown. Stopping.")
                else:
                    distance = None
                    self.log.info(f"Ignoring Error")

                
            # -2: High signal and timeout reached
            # -3: Negative distance
            # -4: Error in time measurement

        return distance, error_occured
    
    def test_distance(self, seconds: int) -> None:
        start_time = time.time()
        t_delta = 0
        while t_delta < seconds:
            t_delta =  time.time() - start_time
            self.log.debug(f"distance: {self.get_distance()} t_delta: {t_delta}")
            time.sleep(0.1)

    
    def drive(self, speed: int = None, angle: int = None) -> None:
        super().drive(speed, angle)


    def stop(self) -> None:
        super().stop()
        self.__us.stop()

    def hard_stop(self) -> None:
        super().hard_stop()
        self.__us.stop()

    def get_log_columns(self) -> List[str]:
        cols = super().get_log_columns() + ['distance', 'delta_t']
        self.log.debug(f"cols for log: {cols}")
        return cols


    def evade_obstacle(self, log_name: str) -> None:
        prev_speed = self.speed
        prev_angle = self.steering_angle

        tmp_angle = self.steering_angle
        if tmp_angle > 90:
            tmp_angle = self.MIN_STEERING_ANGLE
        else:
            tmp_angle = self.MAX_STEERING_ANGLE

        tmp_speed = -30
        tmp_time = 2

        self.log.info(f"Evading with speed {tmp_speed} and angle {tmp_angle} for {tmp_time} seconds")

        self.drive(speed=tmp_speed, angle= tmp_angle)

        start_time = time.time()
        t_delta = time.time() - start_time

        self._running = True
        while (t_delta < tmp_time) and self._running:
            time.sleep(0.25)
            t_delta = time.time() - start_time

            distance, error_occured = self.get_distance(ignore_error=True,
                                                        types_to_ignore=[-1,-2])
            self.log.debug(f"...distance: {distance}, error occured {error_occured}")

            log_data = {"speed" : self.speed, 
                        "angle" : self.steering_angle, 
                        "direction" : self.direction,
                        "distance" : distance,
                        "delta_t" : t_delta
                        }
            
            self.add_log_to_entry(log_name,log_data)

        self.speed = prev_speed 
        self.steering_angle = prev_angle 

        self.log.info(f"evading done")

    def drive_mode(self, mode: str):
        if mode in ("fahrmodus_1", "fahrmodus_2"):
            super().drive_fixed_route(mode)
        else:
            self.random_drive()

    def random_drive(self, stop_at_obstacle: bool = True, normal_speed: int = 30, drive_time: int =20,
                     min_speed: int = 30, max_speed: int = 60):

        from random import normalvariate, randrange

        try:
            ConfigManager.load(base_path = 'config',
                            filenames = 'fahrplan.json',
                            name = "fahrplan"
                            )
            
            cfg = ConfigManager.get(as_attr=True,name="fahrplan")
            stop_distance = cfg.fahrmodus_3.sensor_defs.us_stop_distance
            self.log.debug(f"stop distance: {stop_distance}")
            
            log_name = 'exploration'
            self.new_log_entry(log_name)        

            start_exploration_time = time.time()

            self._running = True
            while(self._running):
                start_time = time.time()

                self.speed = normal_speed

                delta_angle = round(normalvariate(0,20))
                self.steering_angle = self.check_steering_angle(self.steering_angle + delta_angle)

                #delta_speed = randrange(-10,10,5)
                delta_speed = round(normalvariate(0,10))
                tmp_speed = self.speed + delta_speed

                if tmp_speed < min_speed:
                    tmp_speed = min_speed 
                elif tmp_speed > max_speed:
                    tmp_speed = max_speed 

                self.speed = self.check_speed(tmp_speed)
                
                time_for_section = randrange(1,3)


                self.log.info(f"Set new parameters: speed: {self.speed}, angle: {self.steering_angle} for {time_for_section} [s]")
                self.drive(speed=self.speed, angle = self.steering_angle)
                
                t_delta = time.time() - start_time

                while (t_delta < time_for_section) and self._running:
                    time.sleep(0.25)
                    t_delta = time.time() - start_time
                    self.log.debug(f"...time remaining: {t_delta}")

                    distance, error_occured = self.get_distance(ignore_error=True,
                                                                types_to_ignore=[-1,-2])
                    self.log.debug(f"...distance: {distance}, error occured {error_occured}")

                    log_data = {"speed" : self.speed, 
                                "angle" : self.steering_angle, 
                                "direction" : self.direction,
                                "distance" : distance,
                                "delta_t" : t_delta
                                }
                    
                    self.add_log_to_entry(log_name,log_data)
                    
                    if error_occured:
                        tmp_speed = self.speed / 2
                        self.log.info(f"Error occured. Halving speed.")
                        self.drive(speed=tmp_speed)
                        
                        log_data["speed"] = tmp_speed
                        self.add_log_to_entry(log_name,log_data)

                        continue
                    
                    elif distance is None:
                        continue

                    elif distance < stop_distance:
                        if stop_at_obstacle:
                            self.stop()
                            self._running = False
                            break
                        else:
                            self.evade_obstacle(log_name=log_name)
                
                if time.time() - start_exploration_time > drive_time:
                    self._running = False
                    self.log.info(f"drive time limit of {drive_time} seconds reached")

        except Exception as e:
            self.log.error(f"{e}")
        finally:
            self.stop()

if __name__ == "__main__":

    sonic = SonicCar()
    #sonic.test_distance(10)
    sonic.random_drive(stop_at_obstacle = False)
    sonic.log.info(f"complete log:  {sonic.drive_log}")