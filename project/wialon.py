from loguru import logger
from datetime import datetime
import requests
import json

class WialonLogin:
    def __init__(self, sdk_url, auth_token):
        self.sdk_url = sdk_url
        self.logged_in_data = self.login(auth_token)
        self.sid = self.logged_in_data['eid']
        self.user = self.logged_in_data['au']
        self.user_ip = self.logged_in_data['host']
        self.devices = json.loads(self.logged_in_data['user']['prp']['monu'])
    
    def send_wialon_request(self, add_to_sdk_url, post_data) -> dict:
        a = str(requests.get(f'{self.sdk_url}/{add_to_sdk_url}', data=post_data).content, encoding='utf-8')
        return json.loads(a)
    
    def login(self, auth_token):
        return self.send_wialon_request('wialon/ajax.html', {
            'svc': 'token/login',
            'params': json.dumps({
                'token': auth_token
            })
        })
    
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
    

class WialonInfo(WialonLogin):
    def __init__(self, sdk_url, sid):
        self.sdk_url = sdk_url
        self.sid = sid

    def get_user_devices(self):
        output = {}
        a = self.send_wialon_request('wialon/ajax.html', {
            'svc': 'core/search_items',
            'sid': self.sid,
            'params': json.dumps({
                'spec': {
                    'itemsType': 'avl_unit',
                    'propName': 'sys_name',
                    'propValueMask': '*',
                    'sortType': 'sys_name',
                },
                'force': 1,
                'flags': "0x00000001",
                'from': 0,
                'to': 0
            }),
        })
        if 'error' in a:
            return a
        for item in a['items']:
            output[item['id']] = {
                'id': item['id'],
                'name': item['nm'],
            }
        self.devices = output
        return output


    def get_sensors(self, object_id: int):
        json_data = {
            "id": object_id, 
            'flags': "0x00001000"
        }

        response = self.send_wialon_request('wialon/ajax.html', {
            'svc': 'core/search_item',
            'sid': self.sid,
            'params': json.dumps(json_data),
        })

        logger.debug(f"!!!PIZDA!!! {response = } !!!PIZDA!!!")

        return response
        
    def get_fuel(self, object_id: int):
        json_data = {
            "itemId": object_id
        }

        response = self.send_wialon_request('wialon/ajax.html', {
            'svc': 'unit/get_fuel_settings',
            'sid': self.sid,
            'params': json.dumps(json_data),
        })

        logger.debug(f"!!! {response = } !!!")

        return response


    def get_last_events(self):
        return self.send_wialon_request('avl_evts', {'sid': self.sid})
