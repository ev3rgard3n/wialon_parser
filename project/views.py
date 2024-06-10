from django.http import HttpResponse
from django.contrib.auth import logout
from django.shortcuts import render, redirect
from django.conf import settings
from loguru import logger

from .wialon import *


def home_index(request):
    required_keys = {"wialon_sdk_url", "wialon_sid", "wialon_user", "wialon_user_ip"}

    if not required_keys.issubset(request.session.keys()):
        context = {
            "client_id":settings.WIALON_APP_NAME, 
            "redirect_url":settings.WIALON_BACK_URL
        }
        return render(request, "home/auth.html", context)

    sdk_url=request.session.get('wialon_sdk_url', '')
    sid=request.session.get('wialon_sid', '')

    logger.debug(f"{request.session.items() = }")

    new_wialon_devices_info = WialonInfo(sdk_url, sid)
    devices = new_wialon_devices_info.get_user_devices()
    
    output = {
        'wialon_user': request.session.get('wialon_user', None),
        'devices': devices
    }
    print(f"{devices = }")
    return render(request, 'home/index.html', output)


def logout_user(request):
    logout(request)
    context = {
            "client_id":settings.WIALON_APP_NAME, 
            "redirect_url":settings.WIALON_BACK_URL
        }
    return render(request, "home/auth.html", context)


def wialon_send_auth(request):
    return redirect(f'https://hosting.wialon.com/login.html?'\
                    f'client_id={settings.WIALON_APP_NAME}&'\
                    f'redirect_uri={settings.WIALON_BACK_URL}&'\
                    f'response_type=token&'\
                    f'flags=0x1&'\
                    f'lang=ru&'\
                    f'access_type=0x100')


def wialon_recv_auth(request):
    svc_error = int(request.GET.get('svc_error', 0))
    if not svc_error == 0:
        return HttpResponse(f'failed to auth: error {svc_error}')
    sdk_url = request.GET.get('wialon_sdk_url', None)
    auth_token = request.GET.get('access_token', None)
    if sdk_url is None or auth_token is None:
        return HttpResponse('forbidden')
    new_wialon_login = WialonLogin(sdk_url=sdk_url, auth_token=auth_token)

    request.session.flush()
    request.session['wialon_sdk_url'] = new_wialon_login.get_sdk_url()
    request.session['wialon_sid'] = new_wialon_login.get_sid()
    request.session['wialon_user'] = new_wialon_login.get_user()
    request.session['wialon_user_ip'] = new_wialon_login.get_user_ip()
    return redirect('home_index')


def get_sensors(request, object_id) -> dict:
    sdk_url=request.session.get('wialon_sdk_url', '')
    sid=request.session.get('wialon_sid', '')

    logger.debug(f"{sdk_url = } | {sid =}")

    new_wialon_devices_info = WialonInfo(sdk_url, sid)
    sensors = new_wialon_devices_info.get_sensors(object_id)

    print(sensors)
    return HttpResponse(f'sensors {sensors}')


def get_fuel(request, object_id) -> dict:
    sdk_url=request.session.get('wialon_sdk_url', '')
    sid=request.session.get('wialon_sid', '')

    new_wialon_devices_info = WialonInfo(sdk_url, sid)
    sensors = new_wialon_devices_info.get_fuel(object_id)

    print(sensors)
    return HttpResponse(f'fuel {sensors}')


def get_data_from_sensor(request) -> dict:
    """
      https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/unit/update_sensor
    """
    sdk_url=request.session.get('wialon_sdk_url', '')
    sid=request.session.get('wialon_sid', '')

    logger.debug(f"{sdk_url = } | {sid =}")

    new_wialon_devices_info = WialonInfo(sdk_url, sid)
    devices = new_wialon_devices_info.get_user_devices()