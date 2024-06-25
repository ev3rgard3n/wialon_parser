import time
from datetime import datetime, timedelta
from typing import Tuple
from loguru import logger



def convert_to_unix(date_time: datetime) -> time:
    return int(time.mktime(date_time.timetuple()))


def convert_unix_to_datetime(unix_time) -> datetime:
    return datetime.fromtimestamp(unix_time).strftime('%Y-%m-%d %H:%M:%S')


def get_time_start_and_end(flag: str) -> int:
    """ Вычисляет дату начала и окончания промежутка по флагу\n
        Флаг	Описание
        0x00 - начала текущего дня до его конца
        0x02 - начала и конец предыдущего дня
        0x04 - начало и конец предыдущей недели
        0x08 - начало и конец предыдущего месяца
     """
    now = datetime.now()

    if flag == "0x00": 
        start = datetime(now.year, now.month, now.day)
        end = start + timedelta(days=1) - timedelta(seconds=1)

    if flag == "0x02": 
        start = datetime(now.year, now.month, now.day) - timedelta(days=1)
        end = datetime(now.year, now.month, now.day) - timedelta(seconds=1)

    if flag == "0x04": 
        start = now - timedelta(days=now.weekday() + 7)
        start = datetime(start.year, start.month, start.day)
        end = start + timedelta(days=7) - timedelta(seconds=1)

    if flag == "0x08": 
        if now.month == 1:
            start = datetime(now.year - 1, 12, 1)
        else:
            start = datetime(now.year, now.month - 1, 1)

        next_month = start.replace(day=28) + timedelta(days=4)
        end = next_month - timedelta(days=next_month.day)
        end = end.replace(hour=23, minute=59, second=59)

    logger.debug(f"Интервал времени: начало {start} | конец {end}")
    return convert_to_unix(start), convert_to_unix(end)


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


def _rebuilding_sensor_format(sensors: dict) -> dict:
    sensors_ = {"params_with_error": set()}

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
        for key, value in item["p"].items():

            if key in sensors_ and sensors_[key]['type'] == 'fuel level':
                if value > 4096 or value == 65535 or value <= 0:
                    sensors_[key]["data"][time] = value
                    sensors_["params_with_error"].add(key)
                    time = convert_unix_to_datetime(item["t"])

                    logger.debug(f"Найдена ошибка в датчике топлива: {value} at {time}")
    return sensors_
       