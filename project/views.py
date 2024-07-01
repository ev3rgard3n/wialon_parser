from django.http import HttpResponse, JsonResponse
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.conf import settings
from loguru import logger

from project import apis
from project.utils import (
    _rebuilding_devices_format,
    calculate_fuel_theft,
    calculate_total_fuel_difference,
    get_start_param_from_session,
)
from .wialon import *


def home_index(request):
    session_check = check_session_status(request)
    if session_check:
        return session_check
    
    sdk_url, sid, user_id = get_start_param_from_session(request)

    new_wialon_devices_info = WialonInfo(sdk_url, sid, user_id)
    group = new_wialon_devices_info.get_user_devices("avl_unit_group")
    devices = new_wialon_devices_info.get_user_devices()
    
    rebuilding_devices =_rebuilding_devices_format(devices, group)

    output = {
        "wialon_user": request.session.get("wialon_user", None),
        "devices": rebuilding_devices,
    }
    return render(request, "home/index.html", output)


def logout_user(request):
    logout(request)
    return redirect("login")

def login(request):
    context = {
            "client_id": settings.WIALON_APP_NAME,
            "redirect_url": settings.WIALON_BACK_URL,
        }
    return render(request, "home/auth.html", context)


def wialon_send_auth(request):
    return redirect(
        f"https://hosting.wialon.com/login.html?"
        f"client_id={settings.WIALON_APP_NAME}&"
        f"redirect_uri={settings.WIALON_BACK_URL}&"
        f"response_type=token&"
        f"flags=0x1&"
        f"lang=ru&"
        f"access_type=0x100"
    )


def wialon_recv_auth(request):
    svc_error = int(request.GET.get("svc_error", 0))
    logger.debug(f"{request.session.items() = }")
    if not svc_error == 0:
        return HttpResponse(f"failed to auth: error {svc_error}")

    sdk_url = request.GET.get("wialon_sdk_url", None)
    auth_token = request.GET.get("access_token", None)

    if sdk_url is None or auth_token is None:
        return HttpResponse("forbidden")
    new_wialon_login = WialonLogin(sdk_url=sdk_url, auth_token=auth_token)

    request.session.flush()
    request.session["wialon_sdk_url"] = new_wialon_login.get_sdk_url()
    request.session["wialon_sid"] = new_wialon_login.get_sid()
    request.session["wialon_user"] = new_wialon_login.get_user()
    request.session["wialon_user_ip"] = new_wialon_login.get_user_ip()
    request.session["access_token"] = new_wialon_login.get_access_token()
    request.session["user_id"] = new_wialon_login.get_user_id()
    return redirect("home_index")


def get_sensors_statistics(request, object_id) -> dict:
    try:
        session_check = check_session_status(request)
        if session_check:
            return session_check
        sdk_url, sid, user_id = get_start_param_from_session(request)

        flag = request.GET.get("flag", "0x04")

        new_wialon_devices_info = WialonInfo(sdk_url, sid, user_id)
        statistics = new_wialon_devices_info.get_sensors_statistics(object_id, flag)

        return render(request, "report/sensors.html", {"statistics": statistics})
    except Exception as e:
        logger.opt(exception=e).critical(str(e))
        return JsonResponse({"error": str(e)})


def report(request, object_id) -> dict:
    try:
        session_check = check_session_status(request)
        if session_check:
            return session_check
        
        sdk_url, sid, user_id = get_start_param_from_session(request)

        flag = request.GET.get("flag", "0x04")
        date_start = request.GET.get("start", "0")
        date_end = request.GET.get("end", "1")

        new_wialon_devices_info = WialonInfo(sdk_url, sid, user_id)
        json_response = new_wialon_devices_info.fuel_report(
            object_id, flag, date_start, date_end
        )

        data_for_table = calculate_fuel_theft(json_response)
        fuel_theft = calculate_total_fuel_difference(data_for_table)

        context = {
            "object_id": object_id,
            "wialon_user": request.session.get("wialon_user", None),
            "data_for_chart": json.dumps(json_response),
            "data_for_table": data_for_table,
            "fuel_theft": fuel_theft,
            "statistics": new_wialon_devices_info.get_sensors_statistics(object_id, flag)
        }
        return render(request, "report/fuel.html", context)
    except TerminalException as e:
        context = {
            "object_id": object_id,
            "wialon_user": request.session.get("wialon_user", None),
            "fuel_theft": 0,
            "statistics": new_wialon_devices_info.handle_graph_absence(flag)
        }
        logger.opt(exception=e).critical("PORNO")


def report_for_all(request):
    session_check = check_session_status(request)
    if session_check:
        return session_check

    sdk_url, sid, user_id = get_start_param_from_session(request)

    new_wialon_devices_info = WialonInfo(sdk_url, sid, user_id)
    group = new_wialon_devices_info.get_user_devices("avl_unit_group")
    devices = new_wialon_devices_info.get_user_devices()
    
    rebuilding_devices =_rebuilding_devices_format(devices, group)

    context = {
        "wialon_user": request.session.get("wialon_user", None),
        "devices": rebuilding_devices,
    }
    return render(request, "report/report_for_all.html", context)


def sensors_report_for_all(request):
    try:
        sdk_url, sid, user_id = get_start_param_from_session(request)
        new_wialon_devices_info = WialonInfo(sdk_url, sid, user_id)
        flag = request.GET.get("flag", "0x02")
        group_type = request.GET.get("group", "all")
        
        sensor_statistics = new_wialon_devices_info.sensor_statistics_report_for_all(
            flag, group_type
        )
        return JsonResponse(sensor_statistics)

    except Exception as e:
        logger.opt(exception=e).critical(str(e))
        return JsonResponse(None)


def fuel_report_for_all(request):
    try:
        sdk_url, sid, user_id = get_start_param_from_session(request)
        new_wialon_devices_info = WialonInfo(sdk_url, sid, user_id)

        flag = request.GET.get("flag", "0x02")
        date_start = request.GET.get("start", "0")
        date_end = request.GET.get("end", "1")
        group_type = request.GET.get("group", "all")

        fuel_report = new_wialon_devices_info.fuel_report_for_all(
            flag, date_start, date_end, group_type
        )
        return JsonResponse(fuel_report)
    except Exception as e:  
        logger.opt(exception=e).critical(str(e))
        return JsonResponse({"fuel_report": None})


def check_session_status(request):
    required_keys = {"wialon_sdk_url", "wialon_sid", "wialon_user", "wialon_user_ip"}
    session_ = apis.api_wialon_get_last_events(request)
    logger.debug(f"{session_.content}")
    
    try:
        session_data = json.loads(session_.content.decode())
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return redirect("login")
    
    if not required_keys.issubset(request.session.keys()):
        return redirect("login")
    if session_data.get("error") == 1:
        return redirect("login")
    
    return None