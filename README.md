## Настройка виртаульного окружения
python3 -m venv env

source env/bin/activate

pip install requests

pip install django

## Информация по wialon
Для работы необходимо получить token для авторизации приложения

oauth:
https://hosting.wialon.com/login.html?client_id=Wialon&redirect_uri=http://127.0.0.1:8000/wialon_recv_auth/&response_type=token&flags=0x1&lang=ru

back url:
http://dev.vpn.greeb.su:8090/wialon_recv_auth/?lang=ru&success_uri=http%3A%2F%2Fdev%2Evpn%2Egreeb%2Esu%3A8090%2Fwialon_recv_auth%2F&wialon_sdk_url=https%3A%2F%2Fhst%2Dapi%2Ewialon%2Ecom&access_token=5702d603aeb55b9125c105c8cc0b7327844013E57050722C53A9420C487B11B789A729DC&user_name=%D0%93%D0%BB%D0%BE%D0%B1%D0%B0%D0%BB%20%D0%9A%D0%BE%D0%BD%D1%81%D1%82%D1%80%D1%83%D0%BA%D1%82%D0%BE%D1%80&svc_error=0


https://wialon.com/storage/old_en/2015/07/New-Wialon-Authorization-Method_EN.pdf

https://help.wialon.com/help/wialon-hosting/ru/expert-articles/sdk/intro-to-sdk-faq#IntrotoSDK\:FAQ-%D0%9A%D0%B0%D0%BA%D1%81%D0%BE%D0%B7%D0%B4%D0%B0%D1%82%D1%8C%D0%BB%D0%BE%D0%BA%D0%B0%D1%82%D0%BE%D1%80%D1%87%D0%B5%D1%80%D0%B5%D0%B7API\?

https://infostart.ru/1c/articles/672433/

Нужно выполнять каждые минут 5, чтобы сессия не вылетела
https://sdk.wialon.com/wiki/ru/sidebar/remoteapi/apiref/requests/avl_evts
