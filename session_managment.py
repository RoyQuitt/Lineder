import typing
import uuid
from dbUser import MyUser


class Error(Exception):
    """Base class for other exceptions"""
    pass


class Unauthorized(Error):
    print("User unauthorized")
    pass


class SessionManagement:
    def __init__(self):
        self.users_dict: dict[str: str] = {}

    @staticmethod
    def generate_random_uuid():
        return uuid.uuid4()

    def get_address_by_session_id(self, session_id):
        return self.users_dict[session_id]

    def get_key_by_value(self, user_address) -> str:
        return list(self.users_dict.keys())[list(self.users_dict.values()).index(user_address)]

    def login_user(self, user_address: str) -> str:
        new_session_id: str = str(self.generate_random_uuid())
        self.users_dict[new_session_id] = user_address
        # return
        return self.get_key_by_value(user_address)

    def is_logged_in(self, session_id) -> bool:
        return session_id in self.users_dict.keys()

    def log_out(self, session_id):
        del self.users_dict[session_id]

    def handle_user(self, session_id):
        if not self.is_logged_in(session_id):
            raise Unauthorized
        return self.get_address_by_session_id(session_id)

    def handle_user_user_id(self, session_id):
        if not self.is_logged_in(session_id):
            raise Unauthorized
        return self.get_user_id_by_session_id(session_id)

    def get_user_id_by_session_id(self, session_id):
        return MyUser.get_id_by_email(self.get_address_by_session_id(session_id))
