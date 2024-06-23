from datetime import datetime
import time
from typing import Tuple
from loguru import logger


def convert_time_to_unix(date_time: datetime) -> time:
    unix_time = time.mktime(date_time.timetuple())
    logger.debug(f"{unix_time = }")
    logger.debug(f"{type(unix_time) = }")
    return unix_time


def convert_unix_to_datetime(unix_time) -> datetime:
    date_time =  datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')
    logger.debug(f"{date_time}")
    logger.debug(f"{type(date_time)}")
    return date_time


def calculation_fuel_theft(data: dict, type=256) -> list[dict]:
    xData = data["datasets"]["0"]["data"]["x"]
    yData = data["datasets"]["0"]["data"]["y"]
    
    fuel_values_before_and_during_theft = []
    index_time_of_theft = []

    if "markers" in data:
        # Время слива топлива
        time_of_theft = [value for marker in data["markers"] if marker["type"] == type for value in marker["x"]]
        
        # Индексы времени слива топлива
        for x in time_of_theft:
            if x in xData:
                index_time_of_theft.append(xData.index(x))
            else:
                # Найти две ближайшие точки времени до и после
                prev_time = max(filter(lambda y: y < x, xData), default=None)
                next_time = min(filter(lambda y: y > x, xData), default=None)
                
                if prev_time is not None and next_time is not None:
                    index_time_of_theft.append((xData.index(prev_time), xData.index(next_time)))
                elif prev_time is not None:
                    index_time_of_theft.append((xData.index(prev_time),))
                elif next_time is not None:
                    index_time_of_theft.append((xData.index(next_time),))
        
        # Извлечение значений топлива
        fuel_values_before_and_during_theft = []
        for indices in index_time_of_theft:
            if isinstance(indices, int):
                indices = (indices,)  # Преобразовать в кортеж, если это одно целое число
            for index in indices:
                if 0 <= index < len(yData) and index + 1 < len(yData):
                    fuel_value = {
                        "time_of_theft": convert_unix_to_datetime(xData[index]),
                        "fuel_before_theft": yData[index] if index > 0 else None,
                        "fuel_during_theft": yData[index + 1],
                        "fuel_difference": yData[index] - yData[index + 1] if index > 0 else None
                    }
                    fuel_values_before_and_during_theft.append(fuel_value)

    return fuel_values_before_and_during_theft



def calculation_total_fuel_difference(data: list[dict]) -> int:
    return sum([float(item["fuel_difference"]) for item in data])


def calculation_max_and_min_index(count: int | float) -> Tuple[int, int]:
    if count - 500 >= 0: 
        return count - 1, count - 500
    if count - 100 >= 0: 
        return count - 1, count - 100
    
    return count - 1, count - 50


def test_sens(sensors: dict) -> dict:
    sensors_ = {}
    for key, item in sensors.items():
        name = item.get("n")
        type_ = item.get("t")
        param = item.get("p")
        sensors_[param] = {
            "name": name,
            "type": type_,
            "param": param,
            "data": {}
        }
    return sensors_


def exception_sensors_data(sensors_: dict, data: list):
    for item in data[0]:
        time = convert_unix_to_datetime(item["t"])
        logger.debug(f"I = {item}")
        
        for key, value in item["p"].items():
            if key in sensors_ and sensors_[key]['type'] == 'fuel level':
                if value > 4096 or value == 65535 or value == 0:
                    logger.debug(f"Fuel level sensor error detected: {value} at {time}")
                    sensors_[key]["data"][time] = value
    

    return sensors_
       