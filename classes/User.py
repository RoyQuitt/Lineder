from app import Event
from typing import List


class MyUser:
    def __init__(self, username, event_list):
        self.username = username
        self.event_list: List[Event] = event_list

    def insert_new_event(self, new_event: Event):
        self.event_list.append(new_event)

    def set_event_list(self, new_event_list):
        self.event_list = new_event_list

    def get_event_by_title(self, title):
        for event in self.event_list:
            if event.title == title:
                return event
        return None
