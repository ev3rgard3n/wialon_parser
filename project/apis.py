from django.http import JsonResponse, HttpResponse

import requests
import json

from .wialon import *


def api_wialon_get_last_events(request):
    if request.session.get('wialon_sdk_url', None) is None or \
            request.session.get('wialon_sid', None) is None or \
            request.session.get('wialon_user', None) is None or \
            request.session.get('wialon_user_ip', None) is None:
        return HttpResponse('forbidden')

    new_wialon_devices_info = WialonInfo(sdk_url=request.session.get('wialon_sdk_url', ''),
                                         sid=request.session.get('wialon_sid', ''))
    return JsonResponse(new_wialon_devices_info.get_last_events())


def test(request):
    return JsonResponse({'test': 'some data from api'})


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

def first_init(request):
    # a = json.loads(requests.get('https://hst-api.wialon.com/wialon/ajax.html', data={
    #     'svc': 'events/check_updates',
    #     'sid': '03a3d36cc0fd7b41ac6e228cbc3c4e92',
    #     'params': '{"detalization":3}'
    # }).content)
    a = wialon_login()
    eid = a['eid']
    monu = a['user']['prp']['monu']
    df = parse_data(wialon_update_data_flags(monu, eid))

    # c = json.loads(requests.post('https://hst-api.wialon.com/wialon/ajax.html',
    #                              data={'sid': '03a3d36cc0fd7b41ac6e228cbc3c4e92',
    #                                    'params': '{"params":[{"svc":"events/update_units","params":{"mode":"add", "units": []}}],"flags":0}'}).content)
    # l = json.loads(requests.post('https://hst-api.wialon.com/wialon/ajax.html?svc=events/check_updates&params=%7B%22detalization%22%3A3%7D&sid=03acf9252cac984c4ec71403a32f269a').content)
    # return JsonResponse(df, json_dumps_params={'ensure_ascii': False})
    return JsonResponse(df, json_dumps_params={'ensure_ascii': False})
