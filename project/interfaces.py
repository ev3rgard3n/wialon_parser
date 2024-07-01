from abc import ABC, abstractmethod


class WialonI(ABC):

    @abstractmethod
    def send_wialon_request(self, add_to_sdk_url, post_data, method="get") -> dict:
        raise NotImplementedError
    
    @abstractmethod
    def login(self):
        raise NotImplementedError

    @abstractmethod
    def get_sdk_url(self):
        raise NotImplementedError

    @abstractmethod
    def get_sid(self):
        raise NotImplementedError

    @abstractmethod
    def get_user(self):
        raise NotImplementedError

    @abstractmethod
    def get_user_ip(self):
        raise NotImplementedError

    @abstractmethod
    def get_devices(self):
        raise NotImplementedError
    
    @abstractmethod
    def get_access_token(self):
        raise NotImplementedError

    @abstractmethod
    def get_user_id(self):
        raise NotImplementedError