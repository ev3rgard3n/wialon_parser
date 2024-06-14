from datetime import datetime
import time
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


def calculation_fuel_theft(data: dict, type=256) -> dict:
    xData: list = data["datasets"]["0"]["data"]["x"]
    yData: list = data["datasets"]["0"]["data"]["y"]
    
    # Время слива топлива
    time_of_theft = [value for marker in data["markers"] if marker["type"] == type for value in marker["x"]]
    # Индексы времени слива топлива
    index_time_of_theft = [xData.index(x) for x in time_of_theft if x in xData]

    # Извлечение значений топлива
    fuel_values_before_and_during_theft = [
        {
            "time_of_theft": convert_unix_to_datetime(xData[index]),
            "fuel_before_theft": yData[index] if index > 0 else None,
            "fuel_during_theft": yData[index + 1],
            "fuel_difference": yData[index] - yData[index + 1] if index > 0 else None
        }
        for index in index_time_of_theft
    ]
    
    return fuel_values_before_and_during_theft

def calculation_total_fuel_difference(data: list[dict]) -> int:
    total_fuel = [float(item["fuel_difference"]) for item in data]
    
    logger.debug(f"{total_fuel = }")
    return sum(total_fuel)