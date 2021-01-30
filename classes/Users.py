# from app import Event
from classes.User import MyUser
from typing import List


class Users:
    def __init__(self, user_list):
        self.user_list = user_list

    def get_user_by_username(self, username: str) -> MyUser:
        for user in self.user_list:
            if user.username == username:
                return user
        return None

    def insert_new_user(self, new_user: MyUser):
        # if not self.user_list:  # check if first item in the list is '[]', if so, insert the user into that spot
        #     self.user_list[0] = new_user
        if new_user not in self.user_list:
            self.user_list.append(new_user)

    def update_user_event_list(self, username, new_event_list):  # : List[Event]
        for user in self.user_list:
            if user.username == username:
                pass
            else:
                return None
        for user in self.user_list:
            if user.username == username:
                user.event_list = new_event_list
