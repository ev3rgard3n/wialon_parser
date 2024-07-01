import json
import requests

from django.http import JsonResponse, HttpResponse

from .wialon import *


def api_wialon_get_last_events(request):
    if request.session.get('wialon_sdk_url', None) is None or \
            request.session.get('wialon_sid', None) is None or \
            request.session.get('wialon_user', None) is None or \
            request.session.get('wialon_user_ip', None) is None:
        return HttpResponse('forbidden')

    sdk_url=request.session.get('wialon_sdk_url', '')
    sid=request.session.get('wialon_sid', '')
    user_id=request.session.get('user_id', '')

    new_wialon_devices_info = WialonInfo(sdk_url, sid, user_id)
    return JsonResponse(new_wialon_devices_info.get_last_events())


def wialon_login():
    wialon_url = 'https://hst-api.wialon.com/wialon/ajax.html'
    token = '5702d603aeb55b9125c105c8cc0b7327BC5C050E62F788F20E5827C44243DEB08A74955D'
    wialon_params = {
        'token': token
    }
    a = str(requests.get(wialon_url, data={
        'svc': 'token/login',
        'params': json.dumps(wialon_params)
    }).content, encoding='utf-8')
    return json.loads(a)


def wialon_update_data_flags(monu, sid):
    wialon_url = 'https://hst-api.wialon.com/wialon/ajax.html'
    wialon_params = {'spec': []}
    for item in json.loads(monu):
        wialon_params['spec'].append({
            'type': 'id',
            'data': item,
            'flags': 1,
            'mode': 0
        })
    a = str(requests.post(wialon_url, data={
        'svc': 'core/update_data_flags',
        'params': json.dumps(wialon_params),
        'sid': sid,
    }).content, encoding='utf-8')
    return json.loads(a)


def parse_data(data):
    output = {}
    for item in data:
        output[item['i']] = {
            'id': item['d']['id'],
            'name': item['d']['nm'],
        }
    return output