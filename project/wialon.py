import time
from typing import Optional
from loguru import logger
import requests
import json

from project.exceptions import TerminalException
from project.interfaces import WialonI
from project.utils import (
    _rebuilding_sensor_format,
    calculate_fuel_theft,
    calculation_max_and_min_index,
    calculate_total_fuel_difference,
    convert_unix_to_datetime,
    exception_sensors_data,
    get_time_start_and_end,
)


class WialonLogin(WialonI):
    def __init__(
        self,
        sdk_url,
        auth_token,
    ):
        self.sdk_url = sdk_url
        self.access_token = auth_token

        self.logged_in_data = self.login()
        self.sid = self.logged_in_data["eid"]

        self.user = self.logged_in_data["au"]
        self.user_ip = self.logged_in_data["host"]
        self.user_id = self.logged_in_data["user"]["bact"]

        self.devices = json.loads(self.logged_in_data["user"]["prp"]["monu"])

    def send_wialon_request(self, add_to_sdk_url, post_data, method="get") -> dict:
        """TODO: Можно унифицировать"""
        if method.lower() == "get":
            response = str(
                requests.get(
                    f"{self.sdk_url}/{add_to_sdk_url}", data=post_data
                ).content,
                encoding="utf-8",
            )
        if method.lower() == "post":
            response = str(
                requests.post(
                    f"{self.sdk_url}/{add_to_sdk_url}", data=post_data
                ).content,
                encoding="utf-8",
            )

        return json.loads(response)

    def login(self):
        response = self.send_wialon_request(
            "wialon/ajax.html",
            {"svc": "token/login", "params": json.dumps({"token": self.access_token})},
        )
        return response

    def get_sdk_url(self):
        return self.sdk_url

    def get_sid(self):
        return self.sid

    def get_user(self):
        return self.user

    def get_user_ip(self):
        return self.user_ip

    def get_devices(self):
        return self.devices

    def get_access_token(self):
        return self.access_token

    def get_user_id(self):
        return self.user_id


class WialonInfo(WialonLogin):
    def __init__(self, sdk_url, sid, user_id):
        self.sdk_url = sdk_url
        self.sid = sid
        self.user_id = user_id

    def get_user_devices(self, itemsType="avl_unit"):
        output = {}
        response = self.send_wialon_request(
            "wialon/ajax.html",
            {
                "svc": "core/search_items",
                "sid": self.sid,
                "params": json.dumps(
                    {
                        "spec": {
                            "itemsType": itemsType,
                            "propName": "sys_name",
                            "propValueMask": "*",
                            "sortType": "sys_name",
                        },
                        "force": 1,
                        "flags": "0x00000001",
                        "from": 0,
                        "to": 0,
                    }
                ),
            },
        )

        if "error" in response:
            return response
        if itemsType == "avl_unit_group":
            return response

        for item in response["items"]:
            output[item["id"]] = {
                "id": item["id"],
                "name": item["nm"],
            }
        self.devices = output
        return output

    def fuel_report(
        self, object_id: int, flag: str, date_start: str, date_end: str
    ) -> Optional[dict]:

        batch_params = [self.__get_clenup_params()]
        batch_response = self._batch_request(batch_params)
        logger.debug(f"batch_response: {batch_response}")

        self._exec_request(object_id, flag, date_start, date_end)
        apply_report_result = self._check_report_status()
        logger.debug(f"apply_report_result: {apply_report_result}")

        self._check_apply_report_result(apply_report_result)

        json_response = self._get_render_json()
        return json_response

    def _check_apply_report_result(self, data=None) -> TerminalException:
        """
        Проверяет результат отчета на соответствие условиям:
        - attachments пустой
        - bounds состоит из нулей
        
        :param data: Данные отчета для проверки
        :raises TerminalException: Если данные не соответствуют условиям или отсутствуют
        """
        if data is None:
            raise TerminalException("Данные отчета отсутствуют")

        try:
            attachments_empty = not data['reportResult']['attachments']
            
            bounds = data['reportLayer']['bounds']
            bounds_all_zeros = len(bounds) == 4 and all(value == 0 for value in bounds)
            
            if not (attachments_empty and bounds_all_zeros):
                raise TerminalException("Отчет не соответствует условиям: attachments не пуст или bounds содержит ненулевые значения")
            
        except KeyError as e:
            raise TerminalException(f"Отсутствует ожидаемый ключ в данных отчета: {e}")
        return True

    def sensor_statistics_report_for_all(self, flag: str, group_type: str) -> dict:
        devices_with_problem = []
        devices = self.get_user_devices()

        if group_type != "all":
            groups = self.get_user_devices("avl_unit_group")
            groups_items = next(
                (item for item in groups["items"] if item["nm"] == group_type), None
            )
            if groups_items:
                id_arrays = groups_items["u"]
            else:
                id_arrays = devices.keys()
        else:
            id_arrays = devices.keys()

        for device_id in id_arrays:
            device_info = devices.get(device_id)
            if device_info:
                sensors_data = self.get_sensors_statistics(device_id, flag)
                device_info["sensors"] = sensors_data

                if sensors_data["params_with_error"]:
                    devices_with_problem.append(device_id)

        devices["devices_with_problem"] = devices_with_problem
        return devices

    def fuel_report_for_all(
        self, flag: int, date_start: str, date_end: str, group_type: str = "all"
    ) -> dict:
        """
        Получить отчет по топливу для всех устройств или для конкретной группы устройств.

        Args:
            flag (int): Флаг для отчета по топливу.
            date_start (str): Начальная дата.
            date_end (str): Конечная дата.
            group_type (str): Тип группы устройств ("all" для всех устройств или имя группы).

        Returns:
            dict: Словарь устройств с добавленной информацией о кражах топлива.
        """
        devices_with_problem = []
        fuel_theft_total = 0
        devices = self.get_user_devices()

        if group_type != "all":
            groups = self.get_user_devices("avl_unit_group")
            groups_items = next(
                (item for item in groups["items"] if item["nm"] == group_type), None
            )
            if groups_items:
                id_arrays = groups_items["u"]
            else:
                devices["devices_with_problem"] = []
                devices["fuel_theft"] = 0
                return devices
        else:
            id_arrays = devices.keys()  # Все устройства

        for device_id in id_arrays:
            device_info = devices.get(device_id)
            if device_info:
                json_response = self.fuel_report(device_id, flag, date_start, date_end)
                data_for_table = calculate_fuel_theft(json_response)
                fuel_theft = calculate_total_fuel_difference(data_for_table)

                fuel_theft_total += fuel_theft
                if data_for_table:
                    devices_with_problem.append(device_id)
                    device_info["fuel_theft"] = data_for_table

        devices["devices_with_problem"] = devices_with_problem
        devices["fuel_theft"] = fuel_theft_total
        return devices

    def get_sensors_statistics(self, object_id: int, flag: str) -> dict:
        """
        Получение статистики датчиков для заданного объекта и временного интервала.

        Args:
            object_id: ID объекта.
            flag: Флаг, указывающий временной интервал.

        Returns:
            dict: Статистика датчиков или сообщение об ошибке.
        """
        try:
            sensors = self._get_sensors(object_id)
            sensors = _rebuilding_sensor_format(sensors)

            self._remove_layer()
            time_from, time_to = get_time_start_and_end(flag)

            messages = self._fetch_messages(object_id, time_from, time_to)
            logger.debug(f"{messages =}")
            if messages is None:
                return self._handle_no_messages(time_from)
            elif messages.get("error") == 6:
                return self._handle_terminal_absence(time_from)

            return self._process_messages(messages, object_id, sensors)
        except Exception as e:
            logger.opt(exception=e).critical("Ошибка в получении датчиков")
            return {}

    def _fetch_messages(
        self, object_id: int, time_from: int, time_to: int
    ) -> Optional[dict]:
        """
        Получение сообщений для заданного объекта и временного интервала.

        Args:
            object_id: ID объекта.
            time_from (unix): Начало интервала.
            time_to: Конец интервала.

        Returns:
            Optional[dict]: Сообщения или None, если возникла ошибка.
        """
        messages = self._create_messages_layer(object_id, time_from, time_to)
        if messages is None or messages.get("error") == 1001:
            return None
        return messages

    def _handle_no_messages(self, time_from: int) -> dict:
        """
        Обработка ситуации отсутствия сообщений.

        Args:
            time_from (unix): Начало интервала.

        Returns:
            dict: Сообщение об ошибке.
        """
        time_from = convert_unix_to_datetime(time_from)
        return {
            "params_with_error": ["terminal"],
            "terminal": {
                "name": "Потеря сотовой связи",
                "type": "custom",
                "param": "terminal",
                "data": {f"{time_from}": "Нет сообщений для выбранного интервала"},
            },
        }

    def _handle_terminal_absence(self, time_from: int) -> dict:
        """
        Обработка ситуации отсутствия терминала или ТС в системе.

        Args:
            time_from (unix): Начало интервала.

        Returns:
            dict: Сообщение об отсутствии терминала или ТС.
        """
        time_from = convert_unix_to_datetime(time_from)
        return {
            "params_with_error": ["terminal"],
            "terminal": {
                "name": "Терминал",
                "type": "custom",
                "param": "terminal",
                "data": {f"{time_from}": "Нет сообщений для выбранного интервала"},
            },
        }
    
    def handle_graph_absence(self, flag:str) -> dict:
        """
        Обработка ситуации отсутствия терминала или ТС в системе.

        Args:
            time_from (unix): Начало интервала.

        Returns:
            dict: Сообщение об отсутствии терминала или ТС.
        """
        time_from, time_to = get_time_start_and_end(flag)
        return {
            "params_with_error": ["terminal"],
            "terminal": {
                "name": "Терминал",
                "type": "custom",
                "param": "terminal",
                "data": {f"{convert_unix_to_datetime(time_from)}": "Терминал или ТС отсутвуют в системе"},
            },
        }

    def _process_messages(self, messages: dict, object_id: int, sensors: dict) -> dict:
        """
        Обработка полученных сообщений и создание статистики датчиков.

        Args:
            messages (dict): Сообщения.
            object_id (int): Начало интервала.
            sensors (dict): Датчики.

        Returns:
            dict: Статистика датчиков.
        """
        max_index, min_index = calculation_max_and_min_index(
            messages["units"][0]["msgs"]["count"]
        )
        logger.debug(f"Индексы min: {min_index} | max: {max_index}")

        batch_params = [
            self.__get_render_messages_params(min_index, max_index, object_id)
        ]
        statistics = self._batch_request(batch_params)

        return exception_sensors_data(sensors, statistics)

    def get_templates(self):
        """
        Получить все существующие шаблоны
        URL: https://sdk.wialon.com/wiki/ru/local/remoteapi2304/apiref/core/update_data_flags
        """
        return self.send_wialon_request(
            add_to_sdk_url="wialon/ajax.html",
            post_data={
                "svc": "core/update_data_flags",
                "sid": self.sid,
                "params": json.dumps(
                    {
                        "spec": [
                            {
                                "type": "type",
                                "data": "avl_resource",
                                "flags": 8389121,
                                "mode": 1,
                            }
                        ]
                    }
                ),
            },
            method="post",
        )

    def get_template_parameters(self) -> dict:
        """
        Чтобы получить данные о шаблонах отчетов
        URL: https://sdk.wialon.com/wiki/ru/pro/remoteapi/apiref/report/get_report_data
        """
        return {
            "svc": "report/get_report_data",
            "params": {"itemId": self.user_id, "col": ["2"], "flags": 0},
        }

    def _get_sensors(self, object_id: int) -> dict:
        """
        Получить все датчики авто
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/core/search_item
        """
        sensors = self.send_wialon_request(
            "wialon/ajax.html",
            {
                "svc": "core/search_item",
                "sid": self.sid,
                "params": json.dumps({"id": object_id, "flags": "0x00001000"}),
            },
        )

        if "error" in sensors or sensors is None:
            raise Exception()

        return sensors["item"]["sens"]

    def _remove_layer(self, layerName="messages") -> None:
        """
        Чтобы удалить слой
        URl: https://sdk.wialon.com/wiki/ru/local/remoteapi2304/apiref/render/remove_layer
        """
        self.send_wialon_request(
            "wialon/ajax.html",
            {
                "svc": "render/remove_layer",
                "sid": self.sid,
                "params": json.dumps({"layerName": layerName}),
            },
            method="post",
        )

    def _create_messages_layer(
        self, object_id: int, timeFrom: int, timeTo: int
    ) -> dict:
        """
        TODO: Обдумать как время делать

        Чтобы узнать после общее количество существующих записей за время
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/render/create_messages_layer
        """
        response = self.send_wialon_request(
            "wialon/ajax.html",
            {
                "svc": "render/create_messages_layer",
                "sid": self.sid,
                "params": json.dumps(
                    {
                        "layerName": "messages",
                        "itemId": object_id,
                        "timeFrom": timeFrom,
                        "timeTo": timeTo,
                        "tripDetector": 0,
                        "flags": 0,
                        "trackWidth": 4,
                        "trackColor": "cc0000ff",
                        "annotations": 0,
                        "points": 0,
                        "pointColor": "cc0000ff",
                        "arrows": 0,
                    }
                ),
            },
            method="post",
        )
        return response

    def __get_clenup_params(self) -> dict:
        """
        Одновременно в сессии может быть выполнен только один отчет,
        поэтому если в сессии содержаться результаты выполнения предыдущего отчета,
        то перед выполнением следующего отчета их следует удалить командой report/cleanup_result:
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/report/cleanup_result
        """
        return {"svc": "report/cleanup_result", "params": {}}

    def _batch_request(self, params_l: list[dict]) -> list[dict]:
        """
        Несколько команд могут быть выполнены одним запросом
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/core/batch
        """
        try:
            logger.debug(f"Параметры запроса: {params_l}")
            data = {"params": params_l, "flags": 0}
            response = self.send_wialon_request(
                add_to_sdk_url="wialon/ajax.html",
                post_data={
                    "svc": "core/batch",
                    "sid": self.sid,
                    "params": json.dumps(data),
                },
                method="post",
            )
            return response
        except Exception as e:
            logger.opt(exception=e).critical("Ошибка при выполнении запроса")
            return []

    def _exec_request(
        self, object_id: int, interval_flags: str, date_start: int, date_end: int
    ) -> dict:
        """
        Чтобы выполнить отчет
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/report/exec_report
        """
        return self.send_wialon_request(
            add_to_sdk_url="wialon/ajax.html",
            post_data={
                "svc": "report/exec_report",
                "sid": self.sid,
                "params": json.dumps(
                    {
                        "reportResourceId": self.user_id,
                        "reportTemplateId": 2,
                        "reportTemplate": None,
                        "reportObjectId": object_id,
                        "reportObjectSecId": 0,
                        "interval": {
                            "flags": interval_flags,
                            "from": date_start,
                            "to": date_end,
                        },
                        "remoteExec": 1,
                    }
                ),
            },
            method="post",
        )

    def _get_report_status(self) -> dict:
        """
        После выполнения запроса report/exec_report с параметром «remoteExec»:1
        используйте этот запрос report/get_report_status без параметров для получения статуса отчета
        URL: https://sdk.wialon.com/wiki/ru/kit/remoteapi/apiref/report/get_report_status?s[]=report&s[]=apply&s[]=result
        \n 1 - Ожидает очереди | 2 - Выполняется | 4 - Готов | 8 - Отменен | 16 - Ошибка, не удалось найти отчет
        """
        return self.send_wialon_request(
            add_to_sdk_url="wialon/ajax.html",
            post_data={
                "svc": "report/get_report_status",
                "sid": self.sid,
                "params": json.dumps({}),
            },
            method="post",
        )

    def _apply_report_result(self) -> dict:
        """
        После успешного результата(«status»:«4» in response)
        выполните запрос report/apply_report_result без параметров, чтобы получить результат отчета
        URL: https://sdk.wialon.com/wiki/ru/kit/remoteapi/apiref/report/get_report_status?s[]=report&s[]=apply&s[]=result
        """
        return self.send_wialon_request(
            add_to_sdk_url="wialon/ajax.html",
            post_data={
                "svc": "report/apply_report_result",
                "sid": self.sid,
                "params": json.dumps({}),
            },
            method="post",
        )

    def _check_report_status(self) -> Optional[dict]:
        """
        1 - Ожидает очереди | 2 - Выполняется | 4 - Готов \n
        8 - Отменен | 16 - Ошибка, не удалось найти отчет
        """
        while True:
            report_status = self._get_report_status()

            if report_status["status"] == "4":
                return self._apply_report_result()

            elif report_status["status"] in ("1", "2"):
                time.sleep(1)
                continue

            elif report_status["status"] in ("8", "16"):
                break

        return None

    def __get_render_messages_params(self, min_index, max_index, object_id):
        return {
            "svc": "render/get_messages",
            "params": {
                "layerName": "messages",
                "indexFrom": min_index,
                "indexTo": max_index,
                "unitId": object_id,
            },
        }

    def _get_render_json(self) -> dict:
        """
        Чтобы получить JSON графика
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/report/render_json
        """

        return self.send_wialon_request(
            add_to_sdk_url="wialon/ajax.html",
            post_data={
                "svc": "report/render_json",
                "sid": self.sid,
                "params": json.dumps(
                    {
                        "attachmentIndex": 0,
                        "width": 840,
                        "useCrop": 0,
                        "cropBegin": 0,
                        "cropEnd": 0,
                    }
                ),
            },
            method="post",
        )

    def get_last_events(self):
        return self.send_wialon_request("avl_evts", {"sid": self.sid})
