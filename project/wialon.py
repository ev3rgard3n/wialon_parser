import time
from loguru import logger
import requests
import json

from project.utils import _rebuilding_sensor_format, calculation_max_and_min_index, exception_sensors_data, get_time_start_and_end


class WialonLogin:
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

        logger.debug(f"!!!!! {response = }")
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

    def get_user_devices(self):
        output = {}
        a = self.send_wialon_request(
            "wialon/ajax.html",
            {
                "svc": "core/search_items",
                "sid": self.sid,
                "params": json.dumps(
                    {
                        "spec": {
                            "itemsType": "avl_unit",
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
        if "error" in a:
            return a
        for item in a["items"]:
            output[item["id"]] = {
                "id": item["id"],
                "name": item["nm"],
            }
        self.devices = output
        return output

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
        logger.debug(f"Датчики: {sensors}")

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

    def _create_messages_layer(self, object_id: int, timeFrom: int, timeTo: int) -> dict:
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

    def get_sensors_statistics(self, object_id: int, flag: str) -> dict:
        try:

            sensors = self._get_sensors(object_id)
            test_sensors = _rebuilding_sensor_format(sensors)
            
            self._remove_layer()
            timeFrom, timeTo = get_time_start_and_end(flag)
            messages = self._create_messages_layer(object_id, timeFrom, timeTo)
            
            if messages is None or messages.get("error") == 1001:
                return {"regtime-time":{"name":"Потеря сотовой связи", "type":"custom", "param":"regtime-time", "data":{"?":"Возможны проблемы с датчиком"}}}

            max_index, min_index = calculation_max_and_min_index(
                messages["units"][0]["msgs"]["count"]
            )
            logger.debug(f" Индексы min: {min_index} | max: {max_index} ")

            
            statistics = self.send_wialon_request(
                "wialon/ajax.html",
                {
                    "svc": "core/batch",
                    "sid": self.sid,
                    "params": json.dumps(
                        {
                            "params": [
                                {
                                    "svc": "render/get_messages",
                                    "params": {
                                        "layerName": "messages",
                                        "indexFrom": min_index,
                                        "indexTo": max_index,
                                        "unitId": object_id,
                                    },
                                }
                            ],
                            "flags": 0,
                        }
                    ),
                },
                method="post",
            )

            statistics = exception_sensors_data(test_sensors, statistics)
            logger.debug(f"statistics: {statistics}")


            return statistics
        except Exception as e:
            logger.opt(exception=e).critical("Ошибка в получении датчиков")

    def __get_clenup_params(self) -> dict:
        """
        Одновременно в сессии может быть выполнен только один отчет,
        поэтому если в сессии содержаться результаты выполнения предыдущего отчета,
        то перед выполнением следующего отчета их следует удалить командой report/cleanup_result:
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/report/cleanup_result
        """
        return {"svc": "report/cleanup_result", "params": {}}

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
        logger.debug(f"{self.get_templates() = }")
        return {
            "svc": "report/get_report_data",
            "params": {"itemId": self.user_id, "col": ["2"], "flags": 0},
        }

    def _batch_request(self, params_l: list[dict]) -> list[dict]:
        """
        Несколько команд могут быть выполнены одним запросом
        URL: https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/core/batch
        """
        try:
            logger.debug(f"{params_l}")
            data = {"params": params_l}
            return self.send_wialon_request(
                add_to_sdk_url="wialon/ajax.html",
                post_data={
                    "svc": "core/batch",
                    "sid": self.sid,
                    "params": json.dumps(data),
                    "flags": 0,
                },
                method="post",
            )
        except Exception as e:
            logger.opt(exception=e).critical("Error ")

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

    def _check_report_status(self) -> dict | None:
        """
        1 - Ожидает очереди | 2 - Выполняется | 4 - Готов \n
        8 - Отменен | 16 - Ошибка, не удалось найти отчет
        """
        while True:
            report_status = self._get_report_status()

            if report_status["status"] == "4":
                logger.debug(f"Tr {report_status = }")
                return self._apply_report_result()

            elif report_status["status"] in ("1", "2"):
                time.sleep(5)
                continue

            elif report_status["status"] in ("8", "16"):
                break

        return None

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

    def fuel_report(self, object_id: int, flag: str, date_start: str, date_end: str):

        batch_params = [self.__get_clenup_params(), self.get_template_parameters()]
        batch_response = self._batch_request(batch_params)
        logger.debug(f"batch_response: {batch_response}")

        exec_response = self._exec_request(object_id, flag, date_start, date_end)
        apply_report_result = self._check_report_status()

        if apply_report_result is None:
            raise Exception("Ошибка применения результата отчета")

        json_response = self._get_render_json()
        return json_response

    def get_last_events(self):
        return self.send_wialon_request("avl_evts", {"sid": self.sid})
